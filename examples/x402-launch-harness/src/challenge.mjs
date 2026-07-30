import {
  ENDPOINT,
  REQUEST_BODY,
  NETWORK,
  USDT0,
  RECIPIENT,
  FACILITATOR,
  AMOUNT_RAW,
  MAX_AMOUNT_RAW,
} from './config.mjs';

const eq = (a, b) => typeof a === 'string' && typeof b === 'string' && a.toLowerCase() === b.toLowerCase();

export async function fetchChallenge() {
  const response = await fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(REQUEST_BODY),
  });
  if (response.status !== 402) {
    throw new Error(`Expected 402, got ${response.status}`);
  }
  const encoded = response.headers.get('PAYMENT-REQUIRED');
  if (!encoded) throw new Error('Missing PAYMENT-REQUIRED header');
  const challenge = JSON.parse(Buffer.from(encoded, 'base64').toString('utf8'));
  return { status: response.status, challenge };
}

export function selectFlareOption(challenge) {
  const option = (challenge.accepts || []).find(
    (item) => item.network === NETWORK && eq(item.asset, USDT0),
  );
  if (!option) throw new Error(`Expected Flare USD\u20AE0 option is missing`);
  return option;
}

export function assertExpectedTuple(option) {
  const failures = [];
  if (option.scheme !== 'exact') failures.push(`scheme ${option.scheme} != exact`);
  if (option.amount !== AMOUNT_RAW.toString()) failures.push(`amount ${option.amount} != ${AMOUNT_RAW}`);
  if (BigInt(option.amount) > MAX_AMOUNT_RAW) failures.push(`amount above harness ceiling ${MAX_AMOUNT_RAW}`);
  if (!eq(option.payTo, RECIPIENT)) failures.push(`payTo ${option.payTo} != ${RECIPIENT}`);
  if (!eq(option.extra?.facilitator, FACILITATOR)) {
    failures.push(`facilitator ${option.extra?.facilitator} != ${FACILITATOR}`);
  }
  if (option.extra?.eip712Domain?.chainId !== 14) failures.push('eip712 chainId != 14');
  if (!eq(option.extra?.eip712Domain?.verifyingContract, USDT0)) {
    failures.push('eip712 verifyingContract != USD\u20AE0');
  }
  if (!(option.extra?.authorizationTypes || []).includes('transferWithAuthorization')) {
    failures.push('transferWithAuthorization not offered');
  }
  return failures;
}
