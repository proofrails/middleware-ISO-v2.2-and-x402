import type { Address, Hex } from 'viem';
import {
  MOCK_USDT0_ADDRESS,
  RECIPIENT_ADDRESS,
  PAYMENT_AMOUNT_RAW,
} from './contracts';

export interface PaymentPayload {
  from: Address;
  to: Address;
  token: Address;
  value: bigint;
  validAfter: bigint;
  validBefore: bigint;
  nonce: Hex;
  v: number;
  r: Hex;
  s: Hex;
}

export function buildPaymentPayload(userAddress: Address): PaymentPayload {
  const now = Math.floor(Date.now() / 1000);
  // Random 32-byte nonce
  const nonceBytes = new Uint8Array(32);
  crypto.getRandomValues(nonceBytes);
  const nonce = ('0x' + Array.from(nonceBytes).map(b => b.toString(16).padStart(2, '0')).join('')) as Hex;

  // NOTE: MockUSDT0 does not enforce EIP-712 signature recovery.
  // Zero v/r/s is acceptable for this Coston2 testnet flow only.
  return {
    from: userAddress,
    to: RECIPIENT_ADDRESS,
    token: MOCK_USDT0_ADDRESS,
    value: PAYMENT_AMOUNT_RAW,
    validAfter: BigInt(now - 60),
    validBefore: BigInt(now + 900),
    nonce,
    v: 27,
    r: `0x${'00'.repeat(32)}` as Hex,
    s: `0x${'00'.repeat(32)}` as Hex,
  };
}

export function serializePayload(payload: PaymentPayload): Record<string, string> {
  return {
    from: payload.from,
    to: payload.to,
    token: payload.token,
    value: payload.value.toString(),
    validAfter: payload.validAfter.toString(),
    validBefore: payload.validBefore.toString(),
    nonce: payload.nonce,
    v: payload.v.toString(),
    r: payload.r,
    s: payload.s,
  };
}

export function formatAmount(raw: bigint, decimals = 6): string {
  const divisor = BigInt(10 ** decimals);
  const whole = raw / divisor;
  const frac = raw % divisor;
  return `${whole}.${frac.toString().padStart(decimals, '0')}`;
}
