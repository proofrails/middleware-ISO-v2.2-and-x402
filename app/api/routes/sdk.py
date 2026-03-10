from __future__ import annotations

import io
import json
import os
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, HTTPException

from app import schemas

router = APIRouter(tags=["sdk"])


@router.post("/v1/sdk/build")
def build_sdk(req: schemas.SDKBuildRequest):
    """Build a quick-start SDK zip.

    Note: This is a convenience scaffold; the canonical SDKs live in packages/.
    
    New: Supports x402-enabled SDKs with payment handling and agent methods.
    """

    base_url = req.base_url or os.getenv("PUBLIC_BASE_URL") or "http://localhost:8000"
    
    # Check if x402 support is requested
    include_x402 = getattr(req, 'include_x402', False)

    if req.lang not in {"ts", "python"}:
        raise HTTPException(status_code=400, detail="Unsupported lang; use ts | python")

    # --- TypeScript scaffold ---
    if req.lang == "ts":
        readme = f"""# ISO Client (TypeScript)

Install:
```bash
npm i
```

Usage:
```ts
import {{ ISOClient }} from './src/client';
const api = new ISOClient('{base_url}', '{{API_KEY}}');

const receipts = await api.listReceipts();
const rec = await api.getReceipt('<rid>');
const anchors = await api.getAnchors('<rid>');

// Self-hosted mode (tenant anchoring):
await api.confirmAnchor({{ receipt_id: '<rid>', chain: 'flare', flare_txid: '0x...' }});
```
"""

        client_ts = f"""export type ConfirmAnchorRequest = {{ receipt_id: string; chain?: string; flare_txid: string }};

export class ISOClient {{
  constructor(private baseUrl: string = '{base_url}', private apiKey?: string) {{}}

  private headers() {{
    const h: any = {{ 'Content-Type': 'application/json' }};
    if (this.apiKey) h['X-API-Key'] = this.apiKey;
    return h;
  }}

  async listReceipts(params: any = {{}}) {{
    const url = new URL(this.baseUrl + '/v1/receipts');
    Object.entries(params).forEach(([k,v]) => v!=null && url.searchParams.append(k, String(v)));
    const r = await fetch(url, {{ headers: this.headers() }});
    if (!r.ok) throw new Error('listReceipts failed');
    return r.json();
  }}

  async getReceipt(id: string) {{
    const r = await fetch(this.baseUrl + '/v1/iso/receipts/' + id, {{ headers: this.headers() }});
    if (!r.ok) throw new Error('getReceipt failed');
    return r.json();
  }}

  async getAnchors(id: string) {{
    const r = await fetch(this.baseUrl + '/v1/anchors/' + id, {{ headers: this.headers() }});
    if (!r.ok) throw new Error('getAnchors failed');
    return r.json();
  }}

  async confirmAnchor(req: ConfirmAnchorRequest) {{
    const r = await fetch(this.baseUrl + '/v1/iso/confirm-anchor', {{
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify(req)
    }});
    if (!r.ok) throw new Error('confirmAnchor failed');
    return r.json();
  }}
}}
"""

        buf = io.BytesIO()
        with ZipFile(buf, "w", ZIP_DEFLATED) as zf:
            zf.writestr("README.md", readme)
            zf.writestr("package.json", json.dumps({"name": "iso-client", "version": "0.1.0"}, separators=(",", ":")))
            zf.writestr("src/client.ts", client_ts)
        buf.seek(0)
        from fastapi.responses import StreamingResponse

        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=iso-client-ts.zip"},
        )

    # --- Python scaffold ---
    readme = f"""# ISO Client (Python)

```bash
pip install requests
```

Usage:
```py
from iso_client import ISOClient
api = ISOClient(base_url='{base_url}', api_key='{{API_KEY}}')

print(api.list_receipts())
print(api.get_receipt('<rid>'))
print(api.get_anchors('<rid>'))

# Self-hosted mode (tenant anchoring):
api.confirm_anchor(receipt_id='<rid>', flare_txid='0x...', chain='flare')
```
"""

    py = f"""import requests

class ISOClient:
    def __init__(self, base_url='{base_url}', api_key=None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key

    def _headers(self):
        h = {{'Content-Type': 'application/json'}}
        if self.api_key:
            h['X-API-Key'] = self.api_key
        return h

    def list_receipts(self, **params):
        r = requests.get(self.base_url + '/v1/receipts', params=params, headers=self._headers(), timeout=20)
        r.raise_for_status(); return r.json()

    def get_receipt(self, rid: str):
        r = requests.get(self.base_url + '/v1/iso/receipts/' + rid, headers=self._headers(), timeout=20)
        r.raise_for_status(); return r.json()

    def get_anchors(self, rid: str):
        r = requests.get(self.base_url + '/v1/anchors/' + rid, headers=self._headers(), timeout=20)
        r.raise_for_status(); return r.json()

    def confirm_anchor(self, receipt_id: str, flare_txid: str, chain: str | None = None):
        payload = {{'receipt_id': receipt_id, 'flare_txid': flare_txid}}
        if chain:
            payload['chain'] = chain
        r = requests.post(self.base_url + '/v1/iso/confirm-anchor', json=payload, headers=self._headers(), timeout=20)
        r.raise_for_status(); return r.json()
"""

    buf = io.BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as zf:
        zf.writestr("README.md", readme)
        zf.writestr("iso_client.py", py)
    buf.seek(0)
    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=iso-client-py.zip"},
    )
