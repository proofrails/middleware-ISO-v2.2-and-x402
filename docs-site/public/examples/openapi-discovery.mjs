const openapiUrl = process.env.PROOFRAILS_OPENAPI || 'https://app.proofrails.com/openapi.json';
const response = await fetch(openapiUrl);
if (!response.ok) throw new Error(`OpenAPI ${response.status}`);
const schema = await response.json();
const required = [
  ['/v1/iso/record-tip', 'post'],
  ['/v1/iso/receipts/{rid}', 'get'],
  ['/v1/iso/verify', 'post'],
];
for (const [path, method] of required) {
  if (!schema.paths?.[path]?.[method]) throw new Error(`Missing ${method.toUpperCase()} ${path}`);
}
console.log(JSON.stringify({ openapi: schema.openapi, operations: required.length }));
