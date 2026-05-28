import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

let _db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (!_db) {
    const dir = process.env.DATABASE_DIR ?? path.join(process.cwd(), 'data');
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    _db = new Database(path.join(dir, 'unlocks.db'));
    _db.pragma('journal_mode = WAL');
    _db.pragma('foreign_keys = ON');
    initSchema(_db);
  }
  return _db;
}

function initSchema(db: Database.Database) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS unlocks (
      id               TEXT PRIMARY KEY,
      resource_id      TEXT NOT NULL,
      wallet_address   TEXT NOT NULL COLLATE NOCASE,
      chain_id         INTEGER NOT NULL,
      payment_id       TEXT UNIQUE NOT NULL COLLATE NOCASE,
      settlement_tx_hash TEXT NOT NULL COLLATE NOCASE,
      token            TEXT NOT NULL COLLATE NOCASE,
      amount_raw       TEXT NOT NULL,
      recipient        TEXT NOT NULL COLLATE NOCASE,
      status           TEXT NOT NULL DEFAULT 'unlocked',
      receipt_id       TEXT,
      bundle_hash      TEXT,
      verify_url       TEXT,
      error_message    TEXT,
      created_at       TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS feedback (
      id             TEXT PRIMARY KEY,
      wallet_address TEXT,
      payment_id     TEXT,
      message        TEXT NOT NULL,
      rating         INTEGER,
      created_at     TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS analytics_events (
      id         TEXT PRIMARY KEY,
      event      TEXT NOT NULL,
      properties TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);
}
