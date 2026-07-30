#!/usr/bin/env python3
"""Build the committed static ProofRails documentation and machine indexes."""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "site"
BASE = "https://docs.proofrails.com"
CONFIG = json.loads((ROOT / "mint.json").read_text(encoding="utf-8"))
SLUGS = [slug for group in CONFIG["navigation"] for slug in group["pages"]]
LIVE_VERIFIED = {
    "platform-status",
    "x402/status-and-compatibility",
    "x402/mainnet-proof",
    "contracts/flare",
    "deployments",
}


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    meta: dict[str, str] = {}
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            for line in text[4:end].splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip()
            return meta, text[end + 5 :]
    return meta, text


def source_for(slug: str) -> tuple[dict[str, str], str]:
    return frontmatter((ROOT / f"{slug}.mdx").read_text(encoding="utf-8"))


def title_for(slug: str) -> str:
    meta, _ = source_for(slug)
    return meta.get("title", slug.rsplit("/", 1)[-1].replace("-", " ").title())


def url_for(slug: str) -> str:
    return "/" if slug == "introduction" else f"/{slug}"


def canonical_for(slug: str) -> str:
    return f"{BASE}{url_for(slug)}"


def nav(active: str) -> str:
    blocks: list[str] = []
    for group in CONFIG["navigation"]:
        links: list[str] = []
        for slug in group["pages"]:
            cls = ' class="active"' if slug == active else ""
            links.append(
                f'<a{cls} href="{url_for(slug)}">{html.escape(title_for(slug))}</a>'
            )
        blocks.append(
            f'<div class="nav-group"><div class="nav-title">{html.escape(group["group"])}</div>'
            + "".join(links)
            + "</div>"
        )
    return "".join(blocks)


def rewrite_callouts(body: str) -> str:
    body = re.sub(
        r"<Warning>\s*",
        '<div class="callout warning" role="alert"><strong>Real-value warning</strong>',
        body,
    )
    body = re.sub(r"\s*</Warning>", "</div>", body)
    body = re.sub(
        r"<Note>\s*",
        '<div class="callout note"><strong>Note</strong>',
        body,
    )
    body = re.sub(r"\s*</Note>", "</div>", body)
    return body


def previous_next(slug: str) -> str:
    index = SLUGS.index(slug)
    parts: list[str] = []
    if index > 0:
        prior = SLUGS[index - 1]
        parts.append(
            f'<a href="{url_for(prior)}"><span>Previous</span><strong>{html.escape(title_for(prior))}</strong></a>'
        )
    else:
        parts.append("<span></span>")
    if index + 1 < len(SLUGS):
        following = SLUGS[index + 1]
        parts.append(
            f'<a class="next" href="{url_for(following)}"><span>Next</span><strong>{html.escape(title_for(following))}</strong></a>'
        )
    return '<nav class="page-nav">' + "".join(parts) + "</nav>"


def render(slug: str) -> tuple[str, str]:
    meta, source = source_for(slug)
    title = meta.get("title", title_for(slug))
    description = meta.get("description", "ProofRails documentation")
    article = markdown.markdown(
        rewrite_callouts(source),
        extensions=["fenced_code", "tables", "toc", "sane_lists"],
        extension_configs={"toc": {"permalink": False}},
    )
    if slug == "introduction":
        article = re.sub(r"^<h1[^>]*>.*?</h1>\s*", "", article, count=1, flags=re.DOTALL)
    hero = ""
    if slug == "introduction":
        hero = (
            '<section class="hero"><div class="hero-copy">'
            '<div class="hero-eyebrow">ProofRails</div>'
            '<h1>Make onchain payments finance-ready.</h1>'
            '<p>Turn onchain payments and paid API calls into receipts, delivery evidence, '
            'ISO 20022-style artifacts, signed evidence bundles and verifiable onchain commitments.</p>'
            '<div class="hero-links"><a class="primary" href="/quickstart">Use the API</a>'
            '<a href="/product/how-it-works">How it works</a>'
            '<a href="/x402/overview">Understand x402</a></div></div>'
            '<div class="hero-code"><div class="code-bar"><span>RECEIPT API</span>'
            '<span class="code-dots"><i></i><i></i><i></i></span></div>'
            '<pre><span class="method">POST</span> /v1/iso/record-tip\n\n'
            '{\n  <span class="key">"tip_tx_hash"</span>: <span class="string">"0x…"</span>,\n'
            '  <span class="key">"chain"</span>: <span class="string">"flare"</span>,\n'
            '  <span class="key">"amount"</span>: <span class="string">"12.50"</span>,\n'
            '  <span class="key">"currency"</span>: <span class="string">"USD₮0"</span>,\n'
            '  <span class="key">"reference"</span>: <span class="string">"order-1842"</span>\n}\n\n'
            '<span class="comment">receipt_id · evidence.zip · bundle_hash</span></pre></div></section>'
        )
    top = (
        '<header class="topbar"><a class="mobile-brand" href="/">ProofRails</a>'
        '<nav><a href="https://app.proofrails.com">Open app</a>'
        '<a href="/api-reference/overview">API reference</a>'
        '<a href="/agents/machine-readable-docs">AI agent docs</a>'
        '<a href="https://github.com/proofrails/middleware-ISO-v2.2-and-x402">GitHub</a></nav></header>'
    )
    canonical = canonical_for(slug)
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} | ProofRails Docs</title><meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{canonical}"><link rel="alternate" type="text/plain" href="{BASE}/llms-full.txt" title="ProofRails documentation for language models">
<link rel="service-desc" type="application/vnd.oai.openapi+json" href="https://app.proofrails.com/openapi.json">
<link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="/style.css"></head>
<body>{top}<div class="shell"><aside class="sidebar"><a class="brand" href="/"><img src="/proofrails-logo.svg" alt="ProofRails"><div><strong>ProofRails</strong><span>Documentation</span></div></a>{nav(slug)}</aside>
<main class="main">{hero}<article class="content">{article}</article>{previous_next(slug)}<footer>ProofRails · Receipts and evidence for onchain payments</footer></main></div></body></html>'''
    return title, page


def normalize_for_llms(source: str) -> str:
    source = re.sub(r"<Warning>\s*", "**REAL-VALUE WARNING:** ", source)
    source = re.sub(r"\s*</Warning>", "", source)
    source = re.sub(r"<Note>\s*", "**NOTE:** ", source)
    source = re.sub(r"\s*</Note>", "", source)
    source = re.sub(
        r'<img\s+[^>]*alt="([^"]+)"[^>]*/?>',
        lambda match: f"[Diagram: {match.group(1)}]",
        source,
    )
    return source.strip()


def document_type(slug: str) -> str:
    if slug.startswith("api-reference/"):
        return "api-reference"
    if slug.startswith("x402/") or slug.startswith("contracts/"):
        return "protocol-and-onchain"
    if slug.startswith("guides/") or slug.endswith("quickstart"):
        return "guide"
    if slug.startswith("concepts/") or slug.startswith("architecture/"):
        return "concept"
    if slug.startswith("security/"):
        return "security"
    return "product"


def build_machine_indexes() -> None:
    sections: list[str] = [
        "# ProofRails full documentation",
        "",
        "Generated deterministically from the public navigation. Runtime routes remain authoritative in https://app.proofrails.com/openapi.json.",
    ]
    sitemap_entries: list[dict[str, object]] = []
    for slug in SLUGS:
        meta, source = source_for(slug)
        status = "live-verified" if slug in LIVE_VERIFIED else "code-verified"
        sections.extend(
            [
                "",
                "---",
                "",
                f"# {meta.get('title', title_for(slug))}",
                "",
                f"Canonical URL: {canonical_for(slug)}",
                f"Description: {meta.get('description', '')}",
                f"Evidence status: {status}",
                "Last verified: 2026-07-29",
                "",
                normalize_for_llms(source),
            ]
        )
        sitemap_entries.append(
            {
                "url": canonical_for(slug),
                "source": f"{slug}.mdx",
                "title": meta.get("title", title_for(slug)),
                "description": meta.get("description", ""),
                "document_type": document_type(slug),
                "evidence_status": status,
                "last_verified": "2026-07-29",
            }
        )
    (OUT / "llms-full.txt").write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
    (OUT / "sitemap.json").write_text(
        json.dumps({"schema_version": "1.0", "pages": sitemap_entries}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / ".gitignore").write_text(".vercel\n", encoding="utf-8")
    for name in ["favicon.svg", "proofrails-logo.svg", "style.css"]:
        shutil.copy2(ROOT / name, OUT / name)
    if (ROOT / "assets").exists():
        shutil.copytree(ROOT / "assets", OUT / "assets")
    if (ROOT / "public").exists():
        shutil.copytree(ROOT / "public", OUT, dirs_exist_ok=True)

    for slug in SLUGS:
        title, page = render(slug)
        target = OUT / "index.html" if slug == "introduction" else OUT / slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        print(f"built {slug}: {title}")

    (OUT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: https://docs.proofrails.com/sitemap.xml\n",
        encoding="utf-8",
    )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{canonical_for(slug)}</loc></url>\n" for slug in SLUGS)
        + "</urlset>\n"
    )
    (OUT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    build_machine_indexes()
    print(f"built {len(SLUGS)} pages in {OUT}")


if __name__ == "__main__":
    main()
