#!/usr/bin/env python3
"""Deterministic checks for the generated ProofRails static documentation."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
config = json.loads((ROOT / "mint.json").read_text(encoding="utf-8"))
slugs = [p for group in config["navigation"] for p in group["pages"]]
errors: list[str] = []

for slug in slugs:
    source = ROOT / f"{slug}.mdx"
    target = SITE / slug / "index.html"
    if not source.is_file():
        errors.append(f"missing source: {source}")
    if not target.is_file() or target.stat().st_size < 500:
        errors.append(f"missing or empty generated page: {target}")

for page in SITE.rglob("*.html"):
    text = page.read_text(encoding="utf-8")
    if "<title>" not in text or "ProofRails Docs" not in text:
        errors.append(f"missing title: {page}")
    for attr, value in re.findall(r'(href|src)="([^"]+)"', text):
        parsed = urlparse(value)
        if parsed.scheme or value.startswith("#") or value.startswith("mailto:"):
            continue
        clean = value.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            continue
        if clean.startswith("/"):
            rel = clean.lstrip("/")
            candidates = [SITE / rel, SITE / rel / "index.html"]
        else:
            candidates = [page.parent / clean, page.parent / clean / "index.html"]
        if not any(p.exists() for p in candidates):
            errors.append(f"broken {attr} in {page.relative_to(SITE)}: {value}")

required_text = {
    "deployments/index.html": [
        "0x235f83a74fc9D759D648eC533d2c06712F3Ca5EA",
        "0xa78F15ee5a1Ff1D89F6AD782a5f9b81f7C2aA4aE",
        "0xe7cd86e13AC4309349F30B3435a9d337750fC82D",
    ],
    "x402/status-and-compatibility/index.html": [
        "not yet compatible with the standard x402 V2 client flow",
        "PAYMENT-REQUIRED",
        "No signature, retry or transaction followed",
    ],
    "platform-status/index.html": [
        "dde8e2b7-11cb-4ac6-9e32-e4f2c5687ca5",
        "0xf95bb00ef24410243605db07c3c4c46ad64790c191f2dcd020f9e670b88d0c41",
    ],
}
for rel, needles in required_text.items():
    text = (SITE / rel).read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            errors.append(f"required text absent from {rel}: {needle}")

for asset in ["receipt-lifecycle.svg", "evidence-model.svg", "x402-mainnet-flow.svg"]:
    p = SITE / "assets" / asset
    if not p.is_file() or p.stat().st_size < 1000:
        errors.append(f"missing diagram: {asset}")

if errors:
    print("STATIC DOCS VERIFICATION FAILED")
    for error in errors:
        print("-", error)
    raise SystemExit(1)

print(f"STATIC DOCS VERIFICATION PASSED: {len(slugs)} nav pages, {len(list(SITE.rglob('*.html')))} HTML files, 3 diagrams")
