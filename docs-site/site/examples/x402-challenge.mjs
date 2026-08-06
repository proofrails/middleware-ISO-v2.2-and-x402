const endpoint = 'https://app.proofrails.com/v1/x402/premium/fx-lookup';
const response = await fetch(endpoint, {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ base_ccy: 'USD', quote_ccy: 'FLR' }),
});
if (response.status !== 402) throw new Error(`Expected 402, got ${response.status}`);
const encoded = response.headers.get('PAYMENT-REQUIRED');
if (!encoded) throw new Error('Missing PAYMENT-REQUIRED');
const challenge = JSON.parse(Buffer.from(encoded, 'base64').toString('utf8'));
console.log(JSON.stringify(challenge, null, 2));
console.error('Read-only: no signer loaded and no payment submitted.');
