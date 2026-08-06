import { createHmac } from 'crypto';

interface TokenPayload {
  paymentId: string;
  exp: number;
}

export function createResourceToken(paymentId: string): string {
  const payload: TokenPayload = { paymentId, exp: Date.now() + 86_400_000 };
  const b64 = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const sig = createHmac('sha256', getSecret()).update(b64).digest('base64url');
  return `${b64}.${sig}`;
}

export function verifyResourceToken(token: string): string | null {
  const parts = token.split('.');
  if (parts.length !== 2) return null;
  const [b64, sig] = parts;
  const expected = createHmac('sha256', getSecret()).update(b64).digest('base64url');
  if (sig !== expected) return null;
  try {
    const payload = JSON.parse(Buffer.from(b64, 'base64url').toString()) as TokenPayload;
    if (payload.exp < Date.now()) return null;
    return payload.paymentId;
  } catch {
    return null;
  }
}

function getSecret(): string {
  const s = process.env.UNLOCK_SIGNING_SECRET;
  if (!s) throw new Error('UNLOCK_SIGNING_SECRET env var is not set');
  return s;
}
