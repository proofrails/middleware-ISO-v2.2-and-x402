"""RQ worker entrypoint.

Run locally:
  set REDIS_URL=redis://localhost:6379/0
  python worker.py

In Docker Compose, a dedicated `worker` service runs this.
"""

from __future__ import annotations

import logging
import os

from rq import Worker  # type: ignore

from app.queue import get_queue, get_redis

# Configure logging so poller/nonce-manager messages are visible in Docker logs.
# LOG_LEVEL env var controls verbosity (default: INFO). Set to DEBUG for troubleshooting.
_log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s", datefmt="%H:%M:%S"))
for _name in ("middleware.worker", "middleware.anchor_poller", "middleware.jobs", "app.nonce_manager"):
    _logger = logging.getLogger(_name)
    _logger.setLevel(_log_level)
    _logger.addHandler(_handler)
    _logger.propagate = False


def _start_anchor_poller() -> None:
    """Initialise the NonceManager + AnchorPoller for the anchor worker."""
    from web3 import Web3  # type: ignore

    from app.nonce_manager import NonceManager
    from app.anchor_poller import init_poller

    rpc_url = os.getenv("FLARE_RPC_URL", "https://flare-api.flare.network/ext/C/rpc")
    fallback_rpc = os.getenv("FLARE_RPC_URL_FALLBACK", "")
    pk = os.getenv("ANCHOR_PRIVATE_KEY")
    if not pk:
        raise RuntimeError("ANCHOR_PRIVATE_KEY must be set for the anchor worker")

    _log = logging.getLogger("middleware.worker")

    # Try primary RPC, fall back if not connected
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
    try:
        primary_ok = w3.is_connected()
    except Exception:
        primary_ok = False

    if not primary_ok and fallback_rpc:
        _log.warning("primary RPC down (%s), using fallback: %s", rpc_url, fallback_rpc)
        w3 = Web3(Web3.HTTPProvider(fallback_rpc, request_kwargs={"timeout": 30}))
    acct = w3.eth.account.from_key(pk)

    nonce_mgr = NonceManager(w3, acct.address, redis=get_redis())
    poller = init_poller(nonce_manager=nonce_mgr)

    _log.info(
        "anchor_worker_ready address=%s poller_pending=%s",
        acct.address, len(poller._pending),
    )


def _recover_pending_receipts() -> None:
    """Re-enqueue receipts stuck in 'pending' status (never processed).

    Runs on default-queue worker startup so pending receipts survive restarts.
    Uses a Redis set for dedup in case multiple workers start simultaneously.
    """
    from app import db, models
    from app.queue import enqueue_receipt_processing

    _log = logging.getLogger("middleware.worker")
    redis = get_redis()
    dedup_key = "worker:recovery:enqueued"

    session = db.SessionLocal()
    try:
        rows = (
            session.query(models.Receipt)
            .filter(
                models.Receipt.status == "pending",
                models.Receipt.bundle_hash.is_(None),
            )
            .all()
        )
        if not rows:
            return

        count = 0
        for r in rows:
            rid = str(r.id)
            if not redis.sadd(dedup_key, rid):
                continue
            redis.expire(dedup_key, 600)
            enqueue_receipt_processing(receipt_id=rid)
            count += 1

        if count:
            _log.info("recovery_pending count=%d", count)
    except Exception:
        _log.exception("recovery_pending_error")
    finally:
        session.close()


def main() -> None:
    queue_names = [q.strip() for q in (os.getenv("RQ_QUEUES") or "default").split(",") if q.strip()]
    queues = [get_queue(name) for name in queue_names]

    # If this is the anchor worker, start the confirmation poller
    if os.getenv("ANCHOR_WORKER", "").strip() in ("1", "true", "yes"):
        _start_anchor_poller()
    else:
        # Default queue worker: recover any pending receipts from before restart
        _recover_pending_receipts()

    worker = Worker(queues, connection=get_redis())
    # Set default job timeout so stuck jobs don't block the queue forever
    for q in queues:
        if q.DEFAULT_TIMEOUT is None:
            q.DEFAULT_TIMEOUT = 120
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
