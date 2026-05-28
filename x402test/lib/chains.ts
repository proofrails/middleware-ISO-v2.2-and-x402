import { defineChain } from 'viem';

export const coston2 = defineChain({
  id: 114,
  name: 'Flare Coston2',
  nativeCurrency: { name: 'Coston2 Flare', symbol: 'C2FLR', decimals: 18 },
  rpcUrls: {
    default: { http: ['https://coston2-api.flare.network/ext/C/rpc'] },
  },
  blockExplorers: {
    default: {
      name: 'Coston2 Explorer',
      url: 'https://coston2-explorer.flare.network',
    },
  },
  testnet: true,
});

export const FAUCET_URL = 'https://faucet.flare.network/coston2';
export const EXPLORER_TX_URL = (hash: string) =>
  `https://coston2-explorer.flare.network/tx/${hash}`;
