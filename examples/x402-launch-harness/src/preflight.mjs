import { randomBytes } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { toHex, getAddress } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import {
  ENDPOINT,
  RPC_URL,
  CHAIN_ID,
  USDT0,
  RECIPIENT,
  FACILITATOR,
  EVIDENCE_ANCHOR,
  AMOUNT_RAW,
  AMOUNT_DISPLAY,
  AMOUNT_DECIMALS,
  MAX_GAS_WEI,
  RUN_DIR,
  CLIENT_VERSIONS,
  payerPrivateKey,
} from './config.mjs';
import { publicClient, facilitatorAbi, erc20Abi, formatUnits } from './chain.mjs';
import { fetchChallenge, selectFlareOption, assertExpectedTuple } from './challenge.mjs';
import { title, field, check, note, rule } from './format.mjs';

function payerAddress() {
  if (process.env.PAYER_ADDRESS) return getAddress(process.env.PAYER_ADDRESS);
  const key = payerPrivateKey();
  if (key) return privateKeyToAccount(key).address;
  return null;
}

export async function preflight({ quiet = false } = {}) {
  const checks = [];
  const record = (name, ok, detail = '') => {
    checks.push({ name, ok, detail });
    if (!quiet) check(name, ok, detail);
  };

  const { challenge } = await fetchChallenge();
  const option = selectFlareOption(challenge);
  const tupleFailures = assertExpectedTuple(option);

  const [chainId, facilitatorCode, tokenCode, anchorCode] = await Promise.all([
    publicClient.getChainId(),
    publicClient.getCode({ address: FACILITATOR }),
    publicClient.getCode({ address: USDT0 }),
    publicClient.getCode({ address: EVIDENCE_ANCHOR }),
  ]);

  const [paused, supported, minimumAmount, tokenSymbol, tokenDecimals, gasPrice] = await Promise.all([
    publicClient.readContract({ address: FACILITATOR, abi: facilitatorAbi, functionName: 'paused' }),
    publicClient.readContract({
      address: FACILITATOR,
      abi: facilitatorAbi,
      functionName: 'supportedTokens',
      args: [USDT0],
    }),
    publicClient.readContract({
      address: FACILITATOR,
      abi: facilitatorAbi,
      functionName: 'minimumAmounts',
      args: [USDT0],
    }),
    publicClient.readContract({ address: USDT0, abi: erc20Abi, functionName: 'symbol' }),
    publicClient.readContract({ address: USDT0, abi: erc20Abi, functionName: 'decimals' }),
    publicClient.getGasPrice(),
  ]);

  const payer = payerAddress();
  let usdt0Balance = null;
  let flrBalance = null;
  let nonceFresh = null;
  const nonce = toHex(randomBytes(32));
  if (payer) {
    [usdt0Balance, flrBalance] = await Promise.all([
      publicClient.readContract({ address: USDT0, abi: erc20Abi, functionName: 'balanceOf', args: [payer] }),
      publicClient.getBalance({ address: payer }),
    ]);
    const [facilitatorNonceUsed, tokenNonceUsed] = await Promise.all([
      publicClient.readContract({
        address: FACILITATOR,
        abi: facilitatorAbi,
        functionName: 'isNonceUsed',
        args: [USDT0, payer, nonce],
      }),
      publicClient.readContract({
        address: USDT0,
        abi: erc20Abi,
        functionName: 'authorizationState',
        args: [payer, nonce],
      }),
    ]);
    nonceFresh = !facilitatorNonceUsed && !tokenNonceUsed;
  }

  const settlementModes = option.extra?.settlementModes || [];
  const serverSubmitted = settlementModes.includes('server_submitted');
  // 250k gas is a conservative bound for one settlePayment call.
  const feeEstimateWei = gasPrice * 250000n;

  if (!quiet) {
    title('PREFLIGHT \u00b7 no signing, no transaction');
    rule();
    field('ENDPOINT', `POST ${ENDPOINT.replace('https://app.proofrails.com', '')}`);
    field('RPC', RPC_URL);
    field('NETWORK', `Flare mainnet \u00b7 eip155:${chainId}`);
    field('ASSET', `${tokenSymbol} \u00b7 ${tokenDecimals} decimals \u00b7 ${USDT0}`);
    field('AMOUNT', `${AMOUNT_DISPLAY} \u00b7 ${option.amount} raw units`);
    field('PAY TO', RECIPIENT);
    field('FACILITATOR', FACILITATOR);
    field('EVIDENCE ANCHOR', EVIDENCE_ANCHOR);
    field('PAYER', payer || 'not configured');
    field(
      'PAYER USD\u20AE0',
      usdt0Balance === null ? 'unknown' : `${formatUnits(usdt0Balance, AMOUNT_DECIMALS)} ${tokenSymbol}`,
    );
    field('PAYER FLR', flrBalance === null ? 'unknown' : `${formatUnits(flrBalance, 18)} FLR`);
    field('SETTLEMENT MODES', settlementModes.join(', ') || 'none declared');
    field('GAS PRICE', `${formatUnits(gasPrice, 9)} gwei`);
    field('FEE ESTIMATE', `${formatUnits(feeEstimateWei, 18)} FLR @ 250k gas`);
    field('FEE CEILING', `${formatUnits(MAX_GAS_WEI, 18)} FLR`);
    field('CLIENT', Object.entries(CLIENT_VERSIONS).map(([k, v]) => `${k}@${v}`).join(' \u00b7 '));
    rule();
  }

  record('402 challenge served', true, 'PAYMENT-REQUIRED decoded');
  record('Expected payment tuple', tupleFailures.length === 0, tupleFailures.join('; '));
  record('Chain ID is 14', chainId === CHAIN_ID, `rpc reports ${chainId}`);
  record('Facilitator has bytecode', Boolean(facilitatorCode && facilitatorCode !== '0x'));
  record('Token has bytecode', Boolean(tokenCode && tokenCode !== '0x'));
  record('EvidenceAnchor has bytecode', Boolean(anchorCode && anchorCode !== '0x'));
  record('Facilitator not paused', paused === false);
  record('Token supported by facilitator', supported === true);
  record('Minimum amount satisfied', AMOUNT_RAW >= minimumAmount, `minimum ${minimumAmount} raw`);
  record('Payer configured', Boolean(payer));
  record(
    'Payer USD\u20AE0 balance sufficient',
    usdt0Balance !== null && usdt0Balance >= AMOUNT_RAW,
    usdt0Balance === null ? 'no payer configured' : `${formatUnits(usdt0Balance, AMOUNT_DECIMALS)} available`,
  );
  record(
    'Fresh authorization nonce',
    nonceFresh === true,
    nonceFresh === null ? 'no payer configured' : 'unused on facilitator and token',
  );
  record(
    'Gas policy understood',
    serverSubmitted,
    serverSubmitted ? 'server_submitted: ProofRails pays Flare gas' : 'client must pay gas',
  );
  record('Fee estimate under ceiling', feeEstimateWei <= MAX_GAS_WEI, `${formatUnits(feeEstimateWei, 18)} FLR`);
  record('One-broadcast guard enabled', true, 'runs/broadcast.lock');

  const summary = {
    kind: 'preflight',
    generated_at: new Date().toISOString(),
    endpoint: ENDPOINT,
    method: 'POST',
    network: { name: 'Flare mainnet', chain_id: chainId, caip2: `eip155:${chainId}`, rpc: RPC_URL },
    asset: { symbol: tokenSymbol, decimals: Number(tokenDecimals), address: USDT0 },
    amount: { display: '0.001', raw: option.amount },
    recipient: RECIPIENT,
    facilitator: {
      address: FACILITATOR,
      paused,
      token_supported: supported,
      minimum_amount_raw: minimumAmount.toString(),
    },
    evidence_anchor: EVIDENCE_ANCHOR,
    payer: {
      address: payer,
      usdt0_raw: usdt0Balance === null ? null : usdt0Balance.toString(),
      flr_wei: flrBalance === null ? null : flrBalance.toString(),
      nonce_fresh: nonceFresh,
    },
    settlement_modes: settlementModes,
    fees: {
      gas_price_wei: gasPrice.toString(),
      estimate_wei: feeEstimateWei.toString(),
      ceiling_wei: MAX_GAS_WEI.toString(),
      payer_pays_gas: !serverSubmitted,
    },
    client_versions: CLIENT_VERSIONS,
    checks,
    ready_for_record: checks.every((c) => c.ok),
  };

  mkdirSync(RUN_DIR, { recursive: true });
  const out = `${RUN_DIR}preflight-${Date.now()}.json`;
  writeFileSync(out, `${JSON.stringify(summary, null, 2)}\n`);
  if (!quiet) {
    rule();
    note(`preflight written to ${out}`);
    note('No signature was created. No transaction was broadcast.');
  }
  return summary;
}
