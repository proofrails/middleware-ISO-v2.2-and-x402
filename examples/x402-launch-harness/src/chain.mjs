import { createPublicClient, http, defineChain, parseAbi, decodeEventLog } from 'viem';
import { CHAIN_ID, RPC_URL, EXPLORER } from './config.mjs';

export const flare = defineChain({
  id: CHAIN_ID,
  name: 'Flare Mainnet',
  nativeCurrency: { name: 'Flare', symbol: 'FLR', decimals: 18 },
  rpcUrls: { default: { http: [RPC_URL] } },
  blockExplorers: { default: { name: 'Flare Explorer', url: EXPLORER } },
});

export const publicClient = createPublicClient({ chain: flare, transport: http(RPC_URL) });

export const facilitatorAbi = parseAbi([
  'function paused() view returns (bool)',
  'function supportedTokens(address token) view returns (bool)',
  'function minimumAmounts(address token) view returns (uint256)',
  'function isNonceUsed(address token, address authorizer, bytes32 nonce) view returns (bool)',
  'event X402PaymentSettled(address indexed token, address indexed payer, address indexed recipient, uint256 amount, bytes32 nonce, bytes32 paymentId)',
]);

export const erc20Abi = parseAbi([
  'function balanceOf(address owner) view returns (uint256)',
  'function decimals() view returns (uint8)',
  'function symbol() view returns (string)',
  'function authorizationState(address authorizer, bytes32 nonce) view returns (bool)',
]);

export const anchorAbi = parseAbi([
  'event EvidenceAnchored(bytes32 bundleHash, address indexed sender, uint256 ts)',
]);

export function decodeLogs(abi, logs) {
  const out = [];
  for (const log of logs) {
    try {
      out.push({ log, decoded: decodeEventLog({ abi, data: log.data, topics: log.topics }) });
    } catch {
      // not one of ours
    }
  }
  return out;
}

export function formatUnits(raw, decimals) {
  const s = raw.toString().padStart(decimals + 1, '0');
  const whole = s.slice(0, s.length - decimals);
  const frac = s.slice(s.length - decimals).replace(/0+$/, '');
  return frac ? `${whole}.${frac}` : whole;
}
