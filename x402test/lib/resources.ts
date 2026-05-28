import path from 'path';
import fs from 'fs';

const PRIVATE_DIR =
  process.env.RESOURCE_PRIVATE_DIR ?? path.join(process.cwd(), 'resources', 'private');

export function resourcePath(filename: string): string {
  // Sanitize: only allow alphanumeric, dash, underscore, dot
  const safe = filename.replace(/[^a-zA-Z0-9.\-_]/g, '');
  return path.join(PRIVATE_DIR, safe);
}

export function resourceExists(filename: string): boolean {
  return fs.existsSync(resourcePath(filename));
}

export function readResource(filename: string): Buffer | null {
  const p = resourcePath(filename);
  if (!fs.existsSync(p)) return null;
  return fs.readFileSync(p);
}

export const SUPPORTED_RESOURCES: Record<string, { title: string; files: string[] }> = {
  'flare-proofrails-thesis-v1': {
    title: 'Flare x ProofRails: Verifiable Financial Messaging for Onchain Payments',
    files: ['flare-proofrails-thesis-v1.pdf', 'flare-proofrails-thesis-v1.md'],
  },
};

export function contentType(filename: string): string {
  if (filename.endsWith('.pdf')) return 'application/pdf';
  if (filename.endsWith('.md')) return 'text/markdown; charset=utf-8';
  return 'application/octet-stream';
}
