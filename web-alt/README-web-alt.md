# Alternative UI (Next.js)

A standalone, modern web UI for the ISO 20022 Middleware that preserves the gradient background, sticky glass header, 12-column layout, and a persistent right-side AI assistant. This UI runs alongside the Streamlit UI without changing backend behavior.

Contents
- Overview
- Requirements
- Quickstart (local)
- Environment variables
- Features (single-page layout)
- AI Assistant
- Security notes
- Production build
- Troubleshooting

---

Overview
- Path: web-alt/
- Tech: Next.js 14 (app router), TypeScript, Tailwind CSS, lucide-react icons
- Design: Gradient background (slate), sticky translucent header, soft card borders/shadows, 12-col grid
- Layout: Left “Quick Links”, center content with stacked sections, right-side persistent AI assistant

Requirements
- Node.js >= 18.17
- FastAPI backend running and reachable

Backend start (from repo root):
```
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
This exposes the API at http://127.0.0.1:8000 (the default base for the UI).

Quickstart (local)
From repo root:
```
cd web-alt
npm install
npm run dev
```
Open http://localhost:3000

Environment variables
- NEXT_PUBLIC_API_BASE
  - Base URL for the API. Defaults to http://127.0.0.1:8000
  - Example (PowerShell): `$env:NEXT_PUBLIC_API_BASE="http://127.0.0.1:8000"`
- NEXT_PUBLIC_API_KEY (optional)
  - Convenience for local testing if API key auth is enabled on the backend
  - Not recommended to expose in production builds

Features (single-page layout; center column)
- Dashboard + Recent Receipts
  - Lists the latest receipts (id, status, amount, currency, chain, reference, created/anchored timestamps)

- Verify
  - Verify by Bundle URL: POST /v1/iso/verify
    - Input: http://127.0.0.1:8000/files/<rid>/evidence.zip
  - Verify by CID (IPFS/Arweave): POST /v1/iso/verify-cid
    - Inputs: CID (Qm… / bafy… / arweave txid), store (auto/ipfs/arweave), optional receipt_id
  - Displays the resulting JSON including matches_onchain, txid, checksums, and VC hints when present

- SDK Builder + OpenAPI
  - Language: ts | python
  - Packaging: none | npm | pypi
  - Base URL override: defaults to NEXT_PUBLIC_API_BASE
  - Build SDK → POST /v1/sdk/build and download zip
  - Download OpenAPI JSON, and open Swagger UI
  - Usage snippets for TS/Python clients

- Statements
  - camt.053 daily: GET /v1/iso/statements/camt053 (date)
  - camt.052 intraday: GET /v1/iso/statements/camt052 (date + HH:MM-HH:MM window)
  - Displays metadata and a direct “Download” link when available

- Config & Auth (non-secrets)
  - Load config → GET /v1/config
  - Save config → PUT /v1/config
  - Quick editors: security.anchor_mode, security.key_ref, evidence.store.mode, evidence.store.files_base
  - Raw JSON editor for the full non-secret config payload
  - Secrets remain server-side env only

Left column (Quick Links)
- Links to /docs (Swagger) and /openapi.json on the configured API base

Right column (AI Assistant; persistent)
- Scope toggles:
  - Allow reading receipts
  - Restrict to selected receipt_ids (optional) or filters
  - Allow reading artifacts (vc.json)
  - Allow config changes (off by default)
- Endpoint: POST /v1/ai/assist
- Session log: artifacts/ai_sessions/<session_id>.log (download link provided)
- Notes: Provider keys and secrets are not exposed to the browser; assistant only calls server tools that enforce scope.

Security notes
- Do not put secrets in UI or DB:
  - Keep IPFS_TOKEN, BUNDLR_AUTH, ARWEAVE_POST_URL, ANCHOR_PRIVATE_KEY, and any provider auth strictly in server environment.
- API key handling:
  - For local dev convenience, you may set NEXT_PUBLIC_API_KEY, but prefer server-side auth enforcement in production.
- CORS:
  - If hosting the UI separately, ensure the backend allows your UI origin (or proxy via a reverse proxy).

Production build
```
cd web-alt
npm run build
npm start
```
- Ensure NEXT_PUBLIC_API_BASE points to the production API URL.
- Host behind a reverse proxy with TLS (recommended).

Troubleshooting
- Verify failing:
  - Ensure evidence.zip URL is reachable and matches the configured API base
  - Confirm on-chain lookups are available; backend may return anchor_lookup_unavailable if RPC is unreachable
- SDK build failing:
  - Check backend logs for POST /v1/sdk/build
  - If API keys are required, ensure X-API-Key is set (NEXT_PUBLIC_API_KEY for local only)
- Statements returning empty:
  - Check date/window filters and available receipts on that date
- AI assistant errors:
  - Confirm /v1/ai/assist is reachable and server logs show tool execution; scope violations are returned as safe messages
- Node/TypeScript errors:
  - Use Node >= 18.17; rerun npm install; restart dev server

Changelog (this UI)
- 0.1.0:
  - First release; dashboard, verify, SDK builder, statements, config editors (non-secrets), persistent assistant
