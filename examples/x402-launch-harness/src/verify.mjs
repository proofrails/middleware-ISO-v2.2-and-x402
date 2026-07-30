import { execFileSync } from 'node:child_process';
import { createHash, createPublicKey, verify as cryptoVerify } from 'node:crypto';
import { mkdirSync, mkdtempSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { decodeEventLog } from 'viem';
import { EVIDENCE_ANCHOR, FACILITATOR, USDT0, RECIPIENT, AMOUNT_RAW, RUN_DIR } from './config.mjs';
import { publicClient, anchorAbi, facilitatorAbi } from './chain.mjs';
import { title, field, check, note, rule } from './format.mjs';

const sha256 = (buf) => `0x${createHash('sha256').update(buf).digest('hex')}`;
const eq = (a, b) => typeof a === 'string' && typeof b === 'string' && a.toLowerCase() === b.toLowerCase();
const norm = (hash) => (typeof hash === 'string' ? hash.replace(/^0x/, '').toLowerCase() : null);
const hex = (hash) => (typeof hash === 'string' ? `0x${hash.replace(/^0x/, '')}` : hash);

const ED25519_SPKI_PREFIX = Buffer.from('302a300506032b6570032100', 'hex');

// ProofRails serves the Ed25519 public key as a bare 32-byte key inside a
// non-standard "ED25519 PUBLIC KEY" PEM, so wrap it into SPKI when needed.
function loadEd25519PublicKey(pemBytes) {
  const text = pemBytes.toString('utf8');
  try {
    return createPublicKey(text);
  } catch {
    const body = text.replace(/-----[^-]+-----/g, '').replace(/\s+/g, '');
    const raw = Buffer.from(body, 'base64');
    if (raw.length !== 32) throw new Error(`Unsupported public key encoding (${raw.length} bytes)`);
    return createPublicKey({
      key: Buffer.concat([ED25519_SPKI_PREFIX, raw]),
      format: 'der',
      type: 'spki',
    });
  }
}

function verifyManifestSignature(manifestBytes, sigBytes, pemBytes) {
  const key = loadEd25519PublicKey(pemBytes);
  const candidates = [sigBytes];
  const asText = sigBytes.toString('utf8').trim();
  if (/^[A-Za-z0-9+/=\s]+$/.test(asText)) candidates.push(Buffer.from(asText, 'base64'));
  if (/^(0x)?[0-9a-fA-F]+$/.test(asText)) candidates.push(Buffer.from(asText.replace(/^0x/, ''), 'hex'));
  for (const candidate of candidates) {
    try {
      if (cryptoVerify(null, manifestBytes, key, candidate)) return true;
    } catch {
      // try next encoding
    }
  }
  return false;
}

function manifestEntries(manifest) {
  const raw = manifest.files || manifest.entries || manifest.artifacts || [];
  const list = Array.isArray(raw)
    ? raw
    : Object.entries(raw).map(([name, value]) =>
        typeof value === 'string' ? { name, sha256: value } : { name, ...value },
      );
  return list.map((entry) => ({
    name: entry.name || entry.filename || entry.path,
    hash: entry.sha256 || entry.hash || entry.digest,
    size: entry.size ?? entry.bytes ?? null,
  }));
}

export async function verify(receiptId, { runData = null } = {}) {
  if (!receiptId) throw new Error('usage: node harness.mjs verify <receipt_id>');
  const checks = [];
  const add = (name, ok, detail = '') => {
    checks.push({ name, ok, detail });
    check(name, ok, detail);
  };

  const receiptResponse = await fetch(`https://app.proofrails.com/v1/iso/receipts/${receiptId}`);
  if (!receiptResponse.ok) throw new Error(`Receipt fetch failed: ${receiptResponse.status}`);
  const receipt = await receiptResponse.json();

  const bundleUrl = receipt.bundle_url;
  if (!bundleUrl) throw new Error('Receipt exposes no bundle_url');
  const bundleResponse = await fetch(bundleUrl);
  if (!bundleResponse.ok) throw new Error(`Bundle download failed: ${bundleResponse.status}`);
  const bundleBytes = Buffer.from(await bundleResponse.arrayBuffer());
  const bundleHash = sha256(bundleBytes);

  const workDir = mkdtempSync(join(tmpdir(), 'pr-bundle-'));
  const zipPath = join(workDir, 'evidence.zip');
  writeFileSync(zipPath, bundleBytes);
  execFileSync('unzip', ['-q', '-o', zipPath, '-d', join(workDir, 'extracted')]);
  const extracted = join(workDir, 'extracted');

  const manifestBytes = readFileSync(join(extracted, 'manifest.json'));
  const manifest = JSON.parse(manifestBytes.toString('utf8'));
  const sigBytes = readFileSync(join(extracted, 'manifest.sig'));
  const pemBytes = readFileSync(join(extracted, 'public_key.pem'));

  const entries = manifestEntries(manifest);
  const fileResults = entries.map((entry) => {
    try {
      const bytes = readFileSync(join(extracted, entry.name));
      const actual = sha256(bytes);
      const size = statSync(join(extracted, entry.name)).size;
      return {
        ...entry,
        actual,
        actual_size: size,
        ok: norm(actual) === norm(entry.hash) && (entry.size === null || Number(entry.size) === size),
      };
    } catch (error) {
      return { ...entry, ok: false, error: error.message };
    }
  });

  const signatureOk = verifyManifestSignature(manifestBytes, sigBytes, pemBytes);

  let delivery = null;
  try {
    delivery = JSON.parse(readFileSync(join(extracted, 'delivery.json'), 'utf8'));
  } catch {
    delivery = null;
  }
  const deliveryHash =
    delivery?.resource_hash || delivery?.sha256 || delivery?.hash || receipt.resource_hash || null;

  // Settlement transaction facts.
  const settlementTx = runData?.settlement_tx ? hex(runData.settlement_tx) : null;
  let settlement = null;
  if (settlementTx) {
    const txReceipt = await publicClient.getTransactionReceipt({ hash: settlementTx });
    const settledLogs = txReceipt.logs
      .filter((log) => eq(log.address, FACILITATOR))
      .map((log) => {
        try {
          return decodeEventLog({ abi: facilitatorAbi, data: log.data, topics: log.topics });
        } catch {
          return null;
        }
      })
      .filter((decoded) => decoded && decoded.eventName === 'X402PaymentSettled');
    const event = settledLogs[0]?.args || null;
    settlement = {
      status: txReceipt.status,
      block: txReceipt.blockNumber?.toString(),
      event: event
        ? {
            token: event.token,
            payer: event.payer,
            recipient: event.recipient,
            amount: event.amount.toString(),
            nonce: event.nonce,
            payment_id: event.paymentId,
          }
        : null,
      ok:
        txReceipt.status === 'success' &&
        Boolean(event) &&
        eq(event.token, USDT0) &&
        eq(event.recipient, RECIPIENT) &&
        event.amount === AMOUNT_RAW,
    };
  }

  // Onchain anchor.
  const anchorTx = receipt.flare_txid ? hex(receipt.flare_txid) : null;
  let anchor = null;
  if (anchorTx) {
    const anchorReceipt = await publicClient.getTransactionReceipt({ hash: anchorTx });
    const anchorLogs = anchorReceipt.logs
      .filter((log) => eq(log.address, EVIDENCE_ANCHOR))
      .map((log) => {
        try {
          return decodeEventLog({ abi: anchorAbi, data: log.data, topics: log.topics });
        } catch {
          return null;
        }
      })
      .filter((decoded) => decoded && decoded.eventName === 'EvidenceAnchored');
    const event = anchorLogs[0]?.args || null;
    anchor = {
      tx: anchorTx,
      status: anchorReceipt.status,
      contract: EVIDENCE_ANCHOR,
      bundle_hash: event?.bundleHash || null,
      sender: event?.sender || null,
      ts: event?.ts?.toString() || null,
      ok: anchorReceipt.status === 'success' && norm(event?.bundleHash) === norm(bundleHash),
    };
  }

  title('EVIDENCE');
  rule();
  field('RECEIPT', receipt.id);
  field('STATUS', receipt.status);
  field('DELIVERY HASH', deliveryHash || 'not exposed');
  field('ARTIFACTS', fileResults.map((f) => f.name).join(' \u00b7 '));
  field('BUNDLE', `evidence.zip \u00b7 ${bundleBytes.length} bytes`);
  field('BUNDLE HASH', bundleHash);
  field('SIGNATURE', signatureOk ? 'valid Ed25519' : 'INVALID');
  field('ANCHOR TX', anchorTx || 'none');
  field('ANCHOR HASH', anchor?.bundle_hash || 'none');
  rule();
  title('INDEPENDENT CHECKS');

  add(
    'Settlement confirmed',
    settlement ? settlement.ok : false,
    settlement ? `${settlement.event?.amount} raw units \u00b7 block ${settlement.block}` : 'no settlement tx in run data',
  );
  add(
    'Protected result delivered',
    Boolean(runData?.http_status === 200 && runData?.result),
    runData ? `HTTP ${runData.http_status}` : 'no run data',
  );
  add(
    'Receipt automatically linked',
    Boolean(runData?.receipt_id) && runData.receipt_id === receipt.id,
    runData?.receipt_id ? 'PAYMENT-RESPONSE receipt id matches receipt API' : 'no run data',
  );
  add(
    'Delivery hash recorded',
    Boolean(deliveryHash) && (!runData?.response_sha256 || norm(deliveryHash) === norm(runData.response_sha256)),
    deliveryHash ? 'matches delivered bytes' : 'receipt exposes no delivery hash',
  );
  add('Manifest file hashes match', fileResults.every((f) => f.ok), `${fileResults.length} files`);
  add('Bundle signature verified', signatureOk, 'Ed25519 over manifest.json');
  add(
    'Current bundle hash recomputed',
    norm(bundleHash) === norm(receipt.bundle_hash),
    `receipt reports ${receipt.bundle_hash}`,
  );
  add('Flare anchor hash matched', Boolean(anchor?.ok), anchor ? `tx ${anchorTx}` : 'no anchor tx');

  const ok = checks.every((c) => c.ok);
  const result = {
    kind: 'verification',
    generated_at: new Date().toISOString(),
    receipt_id: receipt.id,
    receipt,
    bundle: { url: bundleUrl, bytes: bundleBytes.length, sha256: bundleHash, files: fileResults },
    manifest_signature_valid: signatureOk,
    delivery_hash: deliveryHash,
    settlement,
    anchor,
    checks,
    ok,
  };
  mkdirSync(RUN_DIR, { recursive: true });
  const out = `${RUN_DIR}verification-${receipt.id}.json`;
  writeFileSync(out, `${JSON.stringify(result, null, 2)}\n`);
  rule();
  note(`${ok ? 'ALL CHECKS PASS' : 'VERIFICATION INCOMPLETE'} \u00b7 ${out}`);
  return result;
}
