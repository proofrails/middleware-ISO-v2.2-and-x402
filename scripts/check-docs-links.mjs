/**
 * Check internal markdown links in the docs/ directory.
 * Fails with exit code 1 if any linked file does not exist.
 *
 * Usage: node scripts/check-docs-links.mjs
 */
import { readFileSync, existsSync, readdirSync, statSync } from "fs";
import { join, dirname, resolve } from "path";

import { fileURLToPath } from "url";
const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const DOCS_DIR = join(ROOT, "docs");
const README = join(ROOT, "README.md");

function walkMd(dir) {
  const files = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      files.push(...walkMd(full));
    } else if (entry.endsWith(".md")) {
      files.push(full);
    }
  }
  return files;
}

// Collect all markdown files to check
const mdFiles = [README, ...walkMd(DOCS_DIR)];

// Extract internal markdown links: [text](./relative/path.md) or [text](../path.md)
// Excludes: http/https, anchors-only (#section), mailto
const LINK_RE = /\[([^\]]*)\]\(([^)]+)\)/g;

let errors = 0;
let checked = 0;

for (const file of mdFiles) {
  const content = readFileSync(file, "utf-8");
  const fileDir = dirname(file);
  let match;
  LINK_RE.lastIndex = 0;

  while ((match = LINK_RE.exec(content)) !== null) {
    const href = match[2].split("#")[0].trim(); // strip anchor fragment
    if (!href) continue;                         // anchor-only link
    if (/^https?:\/\//.test(href)) continue;    // external link
    if (/^mailto:/.test(href)) continue;

    const target = resolve(fileDir, href);
    checked++;

    if (!existsSync(target)) {
      console.error(`BROKEN: ${file.replace(ROOT + "/", "")}\n  -> ${href} (resolved: ${target.replace(ROOT + "/", "")})`);
      errors++;
    }
  }
}

console.log(`\nChecked ${checked} internal links in ${mdFiles.length} files.`);

if (errors > 0) {
  console.error(`\n${errors} broken link(s) found.`);
  process.exit(1);
} else {
  console.log("All internal links OK.");
}
