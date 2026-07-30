#!/usr/bin/env python3
"""Deterministic checks for generated ProofRails human and machine documentation."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
BASE = "https://docs.proofrails.com"
CONFIG = json.loads((ROOT / "mint.json").read_text(encoding="utf-8"))
SLUGS = [slug for group in CONFIG["navigation"] for slug in group["pages"]]
ERRORS: list[str] = []


def url_for(slug: str) -> str:
    return "/" if slug == "introduction" else f"/{slug}"


def target_for(slug: str) -> Path:
    return SITE / "index.html" if slug == "introduction" else SITE / slug / "index.html"


# Every source is intentionally published and every navigation entry builds.
source_slugs = {
    str(path.relative_to(ROOT).with_suffix(""))
    for path in ROOT.rglob("*.mdx")
    if "site" not in path.parts
}
if set(SLUGS) != source_slugs:
    for slug in sorted(set(SLUGS) - source_slugs):
        ERRORS.append(f"navigation has no source: {slug}")
    for slug in sorted(source_slugs - set(SLUGS)):
        ERRORS.append(f"orphan MDX is not published: {slug}")
if len(SLUGS) != len(set(SLUGS)):
    ERRORS.append("duplicate navigation slug")

for slug in SLUGS:
    target = target_for(slug)
    if not target.is_file() or target.stat().st_size < 800:
        ERRORS.append(f"missing or empty page: {target}")
        continue
    text = target.read_text(encoding="utf-8")
    canonical = f'{BASE}{url_for(slug)}'
    if f'<link rel="canonical" href="{canonical}">' not in text:
        ERRORS.append(f"wrong canonical: {slug}")
    if 'rel="service-desc"' not in text or "https://app.proofrails.com/openapi.json" not in text:
        ERRORS.append(f"missing OpenAPI discovery link: {slug}")
    if "<Warning>" in text or "</Warning>" in text:
        ERRORS.append(f"unrendered warning: {slug}")
    topbar = text.split('<header class="topbar">', 1)[-1].split("</header>", 1)[0]
    for human_link in [
        'href="/api-reference/overview">API reference</a>',
        'href="/agents/machine-readable-docs">AI agent docs</a>',
    ]:
        if human_link not in topbar:
            ERRORS.append(f"missing human-facing top navigation: {slug}: {human_link}")
    for raw_link in ["openapi.json", "llms.txt"]:
        if raw_link in topbar:
            ERRORS.append(f"raw machine endpoint exposed in top navigation: {slug}: {raw_link}")

# Internal links and assets.
for page in SITE.rglob("*.html"):
    text = page.read_text(encoding="utf-8")
    if "<title>" not in text or "ProofRails Docs" not in text:
        ERRORS.append(f"missing title: {page}")
    for attr, value in re.findall(r'(href|src)="([^"]+)"', text):
        parsed = urlparse(value)
        if parsed.scheme or value.startswith("#") or value.startswith("mailto:"):
            continue
        clean = value.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            continue
        if clean == "/":
            candidates = [SITE / "index.html"]
        elif clean.startswith("/"):
            rel = clean.lstrip("/")
            candidates = [SITE / rel, SITE / rel / "index.html"]
        else:
            candidates = [page.parent / clean, page.parent / clean / "index.html"]
        if not any(candidate.exists() for candidate in candidates):
            ERRORS.append(f"broken {attr} in {page.relative_to(SITE)}: {value}")

if list(SITE.glob("*__*.html")):
    ERRORS.append("duplicate alias HTML files remain")

required_text = {
    "index.html": [
        "Make onchain payments finance-ready.",
        "Where x402 fits",
        "What ProofRails produces",
        "ISO 20022-style artifacts",
    ],
    "product/engine/index.html": ["Resource binding", "awaiting_anchor", "Ed25519"],
    "x402/overview/index.html": ["x402 answers", "PAYMENT-REQUIRED", "Real-value warning"],
    "x402/client-integration/index.html": ["wrapFetchWithPaymentFromConfig", "PAYMENT-RESPONSE", "nonce_already_used"],
    "contracts/flare/index.html": [
        "0x235f83a74fc9D759D648eC533d2c06712F3Ca5EA",
        "0xa78F15ee5a1Ff1D89F6AD782a5f9b81f7C2aA4aE",
        "X402PaymentSettled",
    ],
    "api-reference/receipts/index.html": ["TipRecordRequest", "callback_url", "page-based pagination"],
    "agent-quickstart/index.html": ["Do not invent a", "nonce_already_used", "llms-full.txt"],
}
for rel, needles in required_text.items():
    path = SITE / rel
    if not path.is_file():
        ERRORS.append(f"missing required page: {rel}")
        continue
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            ERRORS.append(f"required text absent from {rel}: {needle}")

for asset in [
    "product-map.svg",
    "x402-role.svg",
    "system-architecture.svg",
    "receipt-lifecycle.svg",
    "evidence-model.svg",
    "x402-mainnet-flow.svg",
]:
    path = SITE / "assets" / asset
    if not path.is_file() or path.stat().st_size < 1000:
        ERRORS.append(f"missing diagram: {asset}")

# Search and agent discovery artifacts.
required_artifacts = [
    "llms.txt",
    "llms-full.txt",
    "sitemap.xml",
    "sitemap.json",
    "contracts.json",
    "capabilities.json",
    ".well-known/proofrails.json",
    "examples/receipt-flow.sh",
    "examples/receipt_flow.py",
    "examples/read-only-proof.sh",
    "examples/openapi-discovery.mjs",
    "examples/x402-challenge.mjs",
]
for rel in required_artifacts:
    path = SITE / rel
    if not path.is_file() or path.stat().st_size == 0:
        ERRORS.append(f"missing machine artifact: {rel}")

json_docs: dict[str, object] = {}
for rel in ["sitemap.json", "contracts.json", "capabilities.json", ".well-known/proofrails.json"]:
    try:
        json_docs[rel] = json.loads((SITE / rel).read_text(encoding="utf-8"))
    except Exception as exc:
        ERRORS.append(f"invalid JSON {rel}: {exc}")

llms_full = (SITE / "llms-full.txt").read_text(encoding="utf-8") if (SITE / "llms-full.txt").is_file() else ""
for slug in SLUGS:
    marker = f"Canonical URL: {BASE}{url_for(slug)}\n"
    if llms_full.count(marker) != 1:
        ERRORS.append(f"llms-full occurrence count is not one: {slug}")

sitemap_doc = json_docs.get("sitemap.json")
if isinstance(sitemap_doc, dict):
    pages = sitemap_doc.get("pages")
    if not isinstance(pages, list) or len(pages) != len(SLUGS):
        ERRORS.append("sitemap.json page count mismatch")

contracts_doc = json_docs.get("contracts.json")
contracts_text = json.dumps(contracts_doc) if contracts_doc else ""
for identity in [
    '"chain_id": 14',
    "0x235f83a74fc9D759D648eC533d2c06712F3Ca5EA",
    "0xa78F15ee5a1Ff1D89F6AD782a5f9b81f7C2aA4aE",
    "0xe7cd86e13AC4309349F30B3435a9d337750fC82D",
]:
    if identity not in contracts_text:
        ERRORS.append(f"contracts registry missing: {identity}")

# Claim and stale-route gates across public source and generated output.
public_text = "\n".join(
    path.read_text(encoding="utf-8", errors="replace")
    for path in list(ROOT.rglob("*.mdx")) + list(SITE.rglob("*.html")) + [SITE / "llms.txt", SITE / "llms-full.txt"]
    if path.is_file()
)
for phrase in [
    "ISO 20022 compliant",
    "ISO 20022 certified",
    "bank-grade",
    "audit-ready",
    "production-ready",
    "enterprise-ready",
]:
    if re.search(re.escape(phrase), public_text, re.IGNORECASE):
        ERRORS.append(f"forbidden claim: {phrase}")
for stale in [
    "/v1/operations/",
    "/retry-anchor",
    "/v1/webhooks",
    "x402/coston2-testnet-demo",
]:
    if stale in public_text:
        ERRORS.append(f"stale or unavailable public route/page: {stale}")

robots = SITE / "robots.txt"
if not robots.is_file() or "Sitemap: https://docs.proofrails.com/sitemap.xml" not in robots.read_text(encoding="utf-8"):
    ERRORS.append("missing or invalid robots.txt")

if ERRORS:
    print("STATIC DOCS VERIFICATION FAILED")
    for error in ERRORS:
        print("-", error)
    raise SystemExit(1)

print(
    f"STATIC DOCS VERIFICATION PASSED: {len(SLUGS)} canonical pages, "
    f"{len(list(SITE.rglob('*.html')))} HTML files, 6 diagrams, "
    f"{len(required_artifacts)} machine artifacts"
)
