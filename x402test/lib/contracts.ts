export const MOCK_USDT0_ADDRESS = '0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8' as const;
export const FACILITATOR_ADDRESS = '0xb59f0d6077A15a3778C262264a83A54B9ABbdEff' as const;
export const RECIPIENT_ADDRESS = '0x0A617D605a1010a74B8dA756E48D75bCef110ef4' as const;

export const PAYMENT_AMOUNT_RAW = 1000n;
export const MIN_AMOUNT_RAW = 1000n;
export const MINT_AMOUNT_RAW = 1_000_000n; // 1.0 MockUSDT0
export const TOKEN_DECIMALS = 6;
export const MIN_GAS_BALANCE = 10_000_000_000_000_000n; // 0.01 C2FLR

export const RESOURCE_ID = 'flare-proofrails-thesis-v1';
export const RESOURCE_TITLE = 'Flare x ProofRails: Verifiable Financial Messaging for Onchain Payments';

export const mockUsdt0Abi = [
  {
    type: 'function',
    name: 'mint',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'to', type: 'address' },
      { name: 'amount', type: 'uint256' },
    ],
    outputs: [],
  },
  {
    type: 'function',
    name: 'balanceOf',
    stateMutability: 'view',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
  {
    type: 'function',
    name: 'decimals',
    stateMutability: 'view',
    inputs: [],
    outputs: [{ name: '', type: 'uint8' }],
  },
  {
    type: 'function',
    name: 'authorizationState',
    stateMutability: 'view',
    inputs: [
      { name: 'authorizer', type: 'address' },
      { name: 'nonce', type: 'bytes32' },
    ],
    outputs: [{ name: '', type: 'bool' }],
  },
] as const;

export const x402FacilitatorAbi = [
  {
    type: 'function',
    name: 'verifyPayment',
    stateMutability: 'view',
    inputs: [
      {
        name: 'payload',
        type: 'tuple',
        components: [
          { name: 'from', type: 'address' },
          { name: 'to', type: 'address' },
          { name: 'token', type: 'address' },
          { name: 'value', type: 'uint256' },
          { name: 'validAfter', type: 'uint256' },
          { name: 'validBefore', type: 'uint256' },
          { name: 'nonce', type: 'bytes32' },
          { name: 'v', type: 'uint8' },
          { name: 'r', type: 'bytes32' },
          { name: 's', type: 'bytes32' },
        ],
      },
    ],
    outputs: [
      { name: 'paymentId', type: 'bytes32' },
      { name: 'valid', type: 'bool' },
    ],
  },
  {
    type: 'function',
    name: 'settlePayment',
    stateMutability: 'nonpayable',
    inputs: [
      {
        name: 'payload',
        type: 'tuple',
        components: [
          { name: 'from', type: 'address' },
          { name: 'to', type: 'address' },
          { name: 'token', type: 'address' },
          { name: 'value', type: 'uint256' },
          { name: 'validAfter', type: 'uint256' },
          { name: 'validBefore', type: 'uint256' },
          { name: 'nonce', type: 'bytes32' },
          { name: 'v', type: 'uint8' },
          { name: 'r', type: 'bytes32' },
          { name: 's', type: 'bytes32' },
        ],
      },
    ],
    outputs: [{ name: 'paymentId', type: 'bytes32' }],
  },
  {
    type: 'function',
    name: 'getPayment',
    stateMutability: 'view',
    inputs: [{ name: 'paymentId', type: 'bytes32' }],
    outputs: [
      {
        type: 'tuple',
        components: [
          { name: 'from', type: 'address' },
          { name: 'to', type: 'address' },
          { name: 'token', type: 'address' },
          { name: 'amount', type: 'uint256' },
          { name: 'nonce', type: 'bytes32' },
          { name: 'timestamp', type: 'uint256' },
          { name: 'settled', type: 'bool' },
        ],
      },
    ],
  },
] as const;
