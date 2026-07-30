export const ENDPOINT = 'https://app.proofrails.com/v1/x402/premium/fx-lookup';
export const REQUEST_BODY = { base_ccy: 'USD', quote_ccy: 'FLR' };

export const CHAIN_ID = 14;
export const NETWORK = 'eip155:14';
export const RPC_URL = process.env.FLARE_RPC_URL || 'https://flare-api.flare.network/ext/C/rpc';
export const EXPLORER = 'https://flare-explorer.flare.network';

export const USDT0 = '0xe7cd86e13AC4309349F30B3435a9d337750fC82D';
export const RECIPIENT = '0x0A617D605a1010a74B8dA756E48D75bCef110ef4';
export const FACILITATOR = '0xa78F15ee5a1Ff1D89F6AD782a5f9b81f7C2aA4aE';
export const EVIDENCE_ANCHOR = '0x235f83a74fc9D759D648eC533d2c06712F3Ca5EA';

export const AMOUNT_RAW = 1000n;
export const AMOUNT_DECIMALS = 6;
export const AMOUNT_DISPLAY = '0.001 USD\u20AE0';

// Hard ceilings. The harness refuses to run `record` if the live challenge
// exceeds any of these.
export const MAX_AMOUNT_RAW = 1000n;
export const MAX_GAS_WEI = 2n * 10n ** 18n; // only relevant on a client-submitted path

export const RUN_DIR = process.env.RUN_DIR || new URL('../runs/', import.meta.url).pathname;
export const BROADCAST_LOCK = `${RUN_DIR}broadcast.lock`;

export function payerPrivateKey() {
  const raw = (process.env.PAYER_PRIVATE_KEY || '').trim();
  if (!raw) return null;
  const hex = raw.startsWith('0x') ? raw.slice(2) : raw;
  if (!/^[0-9a-fA-F]{64}$/.test(hex)) throw new Error('PAYER_PRIVATE_KEY is not a 32-byte hex key');
  return `0x${hex}`;
}

export const CLIENT_VERSIONS = {
  '@x402/fetch': '2.19.0',
  '@x402/evm': '2.19.0',
  viem: '2.37.6',
};
