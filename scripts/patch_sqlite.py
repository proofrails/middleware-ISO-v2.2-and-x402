import os
import sqlite3

DB_PATH = os.path.join(os.getcwd(), "dev.db")


def ensure_column(conn, table, column, ddl):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if column not in cols:
        print(f"Adding column {table}.{column} ...")
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        conn.commit()
    else:
        print(f"Column {table}.{column} already exists.")


def main():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}. Nothing to patch.")
        return
    con = sqlite3.connect(DB_PATH)
    try:
        # Ensure receipts.refund_of exists (SQLite uses TEXT for GUID storage)
        ensure_column(con, "receipts", "refund_of", "TEXT")
        # Multi-tenant additions
        ensure_column(con, "receipts", "project_id", "TEXT")
        ensure_column(con, "api_keys", "project_id", "TEXT")
        ensure_column(con, "api_keys", "role", "TEXT")
        print("Patch complete.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
