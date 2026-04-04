# ProofRails UI

**ProofRails** is a records and evidence layer for **XRP** and **FXRP** payment activity. This package is a **production-style frontend prototype** (React, TypeScript, Tailwind CSS): mock data only, no backend. Use it for demos, screenshots, and product discussions.

## What operators do

1. **Capture** payment events as **Proof Records** (XRPL, FXRP, or programmable), with optional business context.
2. **Monitor** ingest → evidence bundle → **Flare** anchor → verification on the **Proof Records** list and detail views.
3. **Verify** bundle digests against on-chain anchors from the **Verify** page or from a record’s **Verify** action.
4. **Export** ISO-aligned artifacts, JSON, PDF, and sealed bundles from the record detail screen and **Settings** defaults.

## Running locally

```bash
cd proofrails-ui
npm install
npm run dev
```

Open the URL Vite prints (typically `http://localhost:5173`).

```bash
npm run build   # Typecheck + production bundle
npm run preview # Serve dist
```

## Documentation in the app

Full operator documentation (what the product is for, what you can do, and **step-by-step** workflows) lives in the UI:

- Click **Docs** in the top header, or go to **`/docs`**.
- The **Documentation** page covers end-to-end workflow, list/detail/create/verify/settings behavior, and a clear **prototype vs. production** note.

## Main routes

| Path | Purpose |
|------|---------|
| `/records` | **Proof Records** — list, filters, row → detail |
| `/records/create` | **Create Proof Record** — source event + business context |
| `/records/:recordId` | **Proof Record Details** — evidence, Flare anchor, exports |
| `/verify` | **Verify** — ID or bundle hash (+ optional URL) |
| `/settings` | **Settings** — project, API keys, Flare, export defaults |
| `/docs` | **Documentation** — how to use the console |

Sidebar labels remain **Records**, **Verify**, and **Settings** as specified for the MVP shell.

## Tech stack

- **Vite** 8, **React** 19, **TypeScript**
- **Tailwind CSS** v4 via `@tailwindcss/vite`
- **React Router** 7

## Prototype limitations

- All records and actions use **mock data** and **simulated** delays/toasts.
- There is **no** live XRPL or Flare integration in the browser; anchoring and verification results are illustrative until wired to your API and signing infrastructure.

## Project layout (high level)

- `src/pages/` — screen components (Records, Create, Detail, Verify, Settings, Docs)
- `src/components/` — layout (sidebar, header) and reusable UI
- `src/data/mockRecords.ts` — sample Proof Records
- `src/types/record.ts` — shared types

For institutional positioning and UX goals, align demos with the in-app **Documentation** (`/docs`) and keep messaging focused on **Proof Records**, evidence, and Flare anchoring — not trading or wallet features.
