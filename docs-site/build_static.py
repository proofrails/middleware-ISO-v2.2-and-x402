#!/usr/bin/env python3
"""Build the committed static ProofRails docs from docs-site/*.mdx.

Run from the repository root:
  uv run --with markdown python docs-site/build_static.py
"""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "site"
CONFIG = json.loads((ROOT / "mint.json").read_text(encoding="utf-8"))


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


def title_for(slug: str) -> str:
    path = ROOT / f"{slug}.mdx"
    meta, _ = frontmatter(path.read_text(encoding="utf-8"))
    return meta.get("title", slug.rsplit("/", 1)[-1].replace("-", " ").title())


def nav(active: str) -> str:
    blocks = []
    for group in CONFIG["navigation"]:
        links = []
        for slug in group["pages"]:
            cls = ' class="active"' if slug == active else ""
            links.append(f'<a{cls} href="/{slug}">{html.escape(title_for(slug))}</a>')
        blocks.append(
            f'<div class="nav-group"><div class="nav-title">{html.escape(group["group"])}</div>'
            + "".join(links)
            + "</div>"
        )
    return "".join(blocks)


def rewrite_links(body: str) -> str:
    # Mintlify note blocks degrade cleanly in the static build.
    body = re.sub(r"<Note>\s*", '<div class="note">', body)
    body = re.sub(r"\s*</Note>", "</div>", body)
    return body


def render(slug: str) -> tuple[str, str]:
    path = ROOT / f"{slug}.mdx"
    meta, source = frontmatter(path.read_text(encoding="utf-8"))
    title = meta.get("title", title_for(slug))
    description = meta.get("description", "ProofRails documentation")
    source = rewrite_links(source)
    article = markdown.markdown(
        source,
        extensions=["fenced_code", "tables", "toc", "sane_lists"],
        extension_configs={"toc": {"permalink": False}},
    )
    hero = ""
    if slug == "introduction":
        hero = (
            '<section class="hero"><div class="status"><span></span> LIVE ON FLARE MAINNET</div>'
            '<div class="hero-brand"><img src="/proofrails-logo.svg" alt="ProofRails logo">'
            '<strong>ProofRails</strong></div>'
            '<p>Official product and developer documentation</p>'
            '<div class="hero-links"><a class="primary" href="/quickstart">Start building</a>'
            '<a href="/x402/mainnet-proof">Inspect mainnet proof</a>'
            '<a href="/deployments">Contracts</a></div></section>'
        )
    top = (
        '<header class="topbar"><a class="mobile-brand" href="/introduction">ProofRails</a>'
        '<nav><a href="https://app.proofrails.com">App</a>'
        '<a href="https://app.proofrails.com/docs">OpenAPI</a>'
        '<a href="https://github.com/proofrails/middleware-ISO-v2.2-and-x402">GitHub</a></nav></header>'
    )
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} | ProofRails Docs</title><meta name="description" content="{html.escape(description)}">
<link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="/style.css"></head>
<body>{top}<div class="shell"><aside class="sidebar"><a class="brand" href="/introduction"><img src="/proofrails-logo.svg" alt="ProofRails"><div><strong>ProofRails</strong><span>Documentation</span></div></a>{nav(slug)}</aside>
<main class="main">{hero}<article class="content">{article}</article><footer>ProofRails · Verifiable receipts for onchain payments</footer></main></div></body></html>'''
    return title, page


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / ".gitignore").write_text(".vercel\n", encoding="utf-8")
    shutil.copy2(ROOT / "favicon.svg", OUT / "favicon.svg")
    shutil.copy2(ROOT / "proofrails-logo.svg", OUT / "proofrails-logo.svg")
    shutil.copy2(ROOT / "style.css", OUT / "style.css")
    if (ROOT / "assets").exists():
        shutil.copytree(ROOT / "assets", OUT / "assets")

    slugs = [slug for group in CONFIG["navigation"] for slug in group["pages"]]
    for slug in slugs:
        title, page = render(slug)
        target = OUT / slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        alias = OUT / f"{slug.replace('/', '__')}.html"
        alias.write_text(page, encoding="utf-8")
        print(f"built {slug}: {title}")
    shutil.copy2(OUT / "introduction" / "index.html", OUT / "index.html")
    print(f"built {len(slugs)} pages in {OUT}")


if __name__ == "__main__":
    main()
