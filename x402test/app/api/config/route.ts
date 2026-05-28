import { NextResponse } from 'next/server';
import {
  MOCK_USDT0_ADDRESS,
  FACILITATOR_ADDRESS,
  RECIPIENT_ADDRESS,
  RESOURCE_ID,
  RESOURCE_TITLE,
} from '@/lib/contracts';
import { FAUCET_URL } from '@/lib/chains';

export const dynamic = 'force-dynamic';

export function GET() {
  return NextResponse.json({
    network: {
      name: 'Flare Coston2',
      chain_id: 114,
      rpc_url: 'https://coston2-api.flare.network/ext/C/rpc',
      faucet_url: FAUCET_URL,
      explorer_url: 'https://coston2-explorer.flare.network',
    },
    contracts: {
      mock_usdt0: MOCK_USDT0_ADDRESS,
      facilitator: FACILITATOR_ADDRESS,
      recipient: RECIPIENT_ADDRESS,
    },
    price: {
      amount: '0.001',
      raw: '1000',
      decimals: 6,
      currency: 'MockUSDT0',
    },
    resource: {
      id: RESOURCE_ID,
      title: RESOURCE_TITLE,
    },
  });
}
