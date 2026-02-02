#!/usr/bin/env sh
set -e

# Default: run migrations unless explicitly disabled
RUN_MIGRATIONS=${RUN_MIGRATIONS:-1}
AUTO_CREATE_DB=${AUTO_CREATE_DB:-0}
export AUTO_CREATE_DB

if [ "$RUN_MIGRATIONS" = "1" ] || [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "[entrypoint] Running alembic migrations..."

  # If the DB was previously bootstrapped with SQLAlchemy create_all (no alembic_version table)
  # but already contains core tables, we "stamp" the current head to avoid DuplicateTable errors.
  BOOTSTRAP_STAMP=$(python - <<'PY'
import os
import sys

from sqlalchemy import create_engine, text

url = os.getenv("DATABASE_URL")
if not url:
    print("0")
    sys.exit(0)

engine = create_engine(url)
try:
    with engine.connect() as c:
        has_alembic = c.execute(text("select to_regclass('public.alembic_version')")).scalar()
        has_receipts = c.execute(text("select to_regclass('public.receipts')")).scalar()
    if (not has_alembic) and has_receipts:
        print("1")
    else:
        print("0")
except Exception:
    print("0")
PY
  )

  if [ "$BOOTSTRAP_STAMP" = "1" ]; then
    echo "[entrypoint] Existing schema detected without alembic_version; stamping head"
    alembic stamp head
  fi

  alembic upgrade head
else
  echo "[entrypoint] RUN_MIGRATIONS disabled; skipping alembic upgrade"
fi

echo "[entrypoint] Starting: $*"
exec "$@"
