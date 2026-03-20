"""One-off script to re-enqueue stuck/failed receipts for anchoring.

Run inside the API or worker container:
    python retry_failed.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(__file__))

from app import db, models
from app.queue import get_queue, get_redis
from app.jobs import anchor_receipt_job
from sqlalchemy import or_

session = db.SessionLocal()
redis = get_redis()
dedup_key = "anchor:retry:enqueued"

try:
    stuck = (
        session.query(models.Receipt)
        .filter(
            models.Receipt.bundle_hash.isnot(None),
            or_(
                models.Receipt.status == "failed",
                # awaiting_anchor with no txid = tx was never sent
                (models.Receipt.status == "awaiting_anchor") & (models.Receipt.flare_txid.is_(None)),
            ),
        )
        .all()
    )
    print(f"Found {len(stuck)} stuck receipts (failed or awaiting_anchor without txid)")

    anchor_q = get_queue("anchor")
    count = 0
    skipped = 0

    for rec in stuck:
        rid = str(rec.id)
        # Skip if already enqueued by poller or a previous run
        if not redis.sadd(dedup_key, rid):
            skipped += 1
            continue
        redis.expire(dedup_key, 600)

        rec.status = "awaiting_anchor"
        rec.flare_txid = None  # Clear any stale txid

        chains = [
            {
                "name": rec.chain or "flare",
                "contract": os.getenv("ANCHOR_CONTRACT_ADDR", "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8"),
                "rpc_url": os.getenv("FLARE_RPC_URL"),
            }
        ]

        anchor_q.enqueue(
            anchor_receipt_job,
            receipt_id=rid,
            bundle_hash=rec.bundle_hash,
            chains=chains,
            job_timeout=int(os.getenv("ANCHOR_JOB_TIMEOUT", "120")),
        )
        count += 1

    session.commit()
    print(f"Re-enqueued {count} receipts to anchor queue (skipped {skipped} already enqueued)")

finally:
    session.close()
