import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { wrapFetchWithPaymentFromConfig, decodePaymentResponseHeader } from '@x402/fetch';
import { ExactEvmScheme, toClientEvmSigner } from '@x402/evm';
import { privateKeyToAccount } from 'viem/accounts';
import {
  ENDPOINT,
  REQUEST_BODY,
  NETWORK,
  EXPLORER,
  RUN_DIR,
  BROADCAST_LOCK,
  AMOUNT_DISPLAY,
  payerPrivateKey,
} from './config.mjs';
import { preflight } from './preflight.mjs';
import { publicClient } from './chain.mjs';
import { selectFlareOption, assertExpectedTuple } from './challenge.mjs';
import { title, field, note, rule, check } from './format.mjs';
import { verify } from './verify.mjs';

const RECEIPT_POLL_INTERVAL_MS = 3000;
const RECEIPT_POLL_TIMEOUT_MS = 10 * 60 * 1000;

function pick(source, keys) {
  for (const key of keys) {
    const containers = [source, source?.extra, source?.extensions];
    for (const container of containers) {
      if (container && container[key] !== undefined && container[key] !== null) return container[key];
    }
  }
  return null;
}

async function pollReceipt(receiptId, onState) {
  const started = Date.now();
  let lastState = null;
  for (;;) {
    const response = await fetch(`https://app.proofrails.com/v1/iso/receipts/${receiptId}`);
    if (response.ok) {
      const receipt = await response.json();
      if (receipt.status !== lastState) {
        lastState = receipt.status;
        onState(receipt);
      }
      if (receipt.status === 'anchored' || receipt.status === 'failed') return receipt;
    }
    if (Date.now() - started > RECEIPT_POLL_TIMEOUT_MS) {
      throw new Error(`Receipt ${receiptId} did not reach a terminal state within the poll window`);
    }
    await new Promise((resolve) => setTimeout(resolve, RECEIPT_POLL_INTERVAL_MS));
  }
}

export async function record({ approvalToken } = {}) {
  mkdirSync(RUN_DIR, { recursive: true });

  const privateKey = payerPrivateKey();
  if (!privateKey) throw new Error('PAYER_PRIVATE_KEY is not set');
  if (!approvalToken) {
    throw new Error('APPROVED_PAYMENT_ID is not set: one real payment requires explicit approval');
  }
  if (existsSync(BROADCAST_LOCK)) {
    throw new Error(
      `One-broadcast guard: ${BROADCAST_LOCK} exists. A signed payment was already attempted; refusing to pay again.`,
    );
  }

  const pre = await preflight({ quiet: true });
  if (!pre.ready_for_record) {
    const failed = pre.checks.filter((c) => !c.ok).map((c) => c.name);
    throw new Error(`Preflight not clean, refusing to pay: ${failed.join(', ')}`);
  }

  const account = privateKeyToAccount(privateKey);
  // Never let option ordering decide what gets signed: the challenge also offers
  // a 0.05 native FLR option on the same network.
  const selectExactTuple = (x402Version, accepts) => {
    const option = selectFlareOption({ accepts });
    const failures = assertExpectedTuple(option);
    if (failures.length) throw new Error(`Offered option is not the approved tuple: ${failures.join('; ')}`);
    return option;
  };

  const paidFetch = wrapFetchWithPaymentFromConfig(fetch, {
    schemes: [{ network: NETWORK, client: new ExactEvmScheme(toClientEvmSigner(account, publicClient)) }],
    paymentRequirementsSelector: selectExactTuple,
  });

  title(`PAID REQUEST \u00b7 FLARE MAINNET \u00b7 REAL VALUE \u00b7 ${AMOUNT_DISPLAY}`);
  rule();
  field('APPROVAL', approvalToken);
  field('PAYER', account.address);
  field('REQUEST', `POST ${ENDPOINT.replace('https://app.proofrails.com', '')}`);

  // Everything after this line may spend real value exactly once.
  writeFileSync(
    BROADCAST_LOCK,
    `${JSON.stringify({ approval: approvalToken, payer: account.address, started_at: new Date().toISOString() }, null, 2)}\n`,
  );

  field('PAYMENT-SIGNATURE', 'created locally');
  const response = await paidFetch(ENDPOINT, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(REQUEST_BODY),
  });

  const paymentHeader = response.headers.get('PAYMENT-RESPONSE');
  const rawBody = Buffer.from(await response.arrayBuffer());
  const bodyText = rawBody.toString('utf8');
  const requestId = response.headers.get('x-request-id');

  if (!response.ok) {
    writeFileSync(
      `${RUN_DIR}record-failed-${Date.now()}.json`,
      `${JSON.stringify({ status: response.status, body: bodyText, request_id: requestId }, null, 2)}\n`,
    );
    throw new Error(`Paid request returned ${response.status}. Not retrying a signed payment.`);
  }
  if (!paymentHeader) throw new Error('Missing PAYMENT-RESPONSE header on a 200 response');

  const payment = decodePaymentResponseHeader(paymentHeader);
  const settlementTx = pick(payment, ['transaction', 'settlement_tx', 'txHash']);
  const receiptId = pick(payment, ['receiptId', 'receipt_id']);
  const receiptUrl = pick(payment, ['receiptUrl', 'receipt_url']);
  const verifierUrl = pick(payment, ['verifierUrl', 'verifier_url']);
  const resourceHash = pick(payment, ['resourceHash', 'resource_hash']);
  const result = JSON.parse(bodyText);

  field('SETTLEMENT', 'confirmed on Flare mainnet');
  field('RETRY', 'same endpoint');
  field('RESOURCE', `${response.status} OK`);
  field('PAYMENT-RESPONSE', 'received');
  rule();
  title('DELIVERED RESULT');
  for (const [key, value] of Object.entries(result)) field(key.toUpperCase(), String(value));
  rule();
  title('DECODED PUBLIC EVIDENCE');
  field('settlement_tx', settlementTx || 'not returned');
  field('receipt_id', receiptId || 'not returned');
  field('receipt_url', receiptUrl || 'not returned');
  field('verifier_url', verifierUrl || 'not returned');
  field('resource_hash', resourceHash || 'not returned');
  field('local sha256(body)', `0x${createHash('sha256').update(rawBody).digest('hex')}`);
  note(`${EXPLORER}/tx/${settlementTx}`);

  const runPath = `${RUN_DIR}run-${receiptId || Date.now()}.json`;
  const runData = {
    kind: 'record',
    approval: approvalToken,
    payer: account.address,
    request_id: requestId,
    http_status: response.status,
    result,
    response_sha256: `0x${createHash('sha256').update(rawBody).digest('hex')}`,
    settlement_tx: settlementTx,
    receipt_id: receiptId,
    receipt_url: receiptUrl,
    verifier_url: verifierUrl,
    resource_hash: resourceHash,
    payment_response: payment,
    preflight: pre,
    started_at: new Date().toISOString(),
  };
  writeFileSync(runPath, `${JSON.stringify(runData, null, 2)}\n`);

  if (!receiptId) throw new Error('No receipt reference returned; cannot follow the evidence workflow');

  rule();
  title('RECEIPT LIFECYCLE');
  const receipt = await pollReceipt(receiptId, (r) => {
    field('STATE', `${r.status}${r.bundle_hash ? ` \u00b7 bundle ${r.bundle_hash}` : ''}`);
  });
  writeFileSync(runPath, `${JSON.stringify({ ...runData, receipt }, null, 2)}\n`);

  if (receipt.status !== 'anchored') {
    check('Receipt anchored', false, `terminal state ${receipt.status}`);
    throw new Error(`Receipt ended in ${receipt.status}. Run marked failed; no second payment.`);
  }

  rule();
  const verification = await verify(receiptId, { runData: { ...runData, receipt } });
  return { ok: verification.ok, receiptId, settlementTx, runPath };
}
