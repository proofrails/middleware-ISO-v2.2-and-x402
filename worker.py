"""RQ worker entrypoint.

Run locally:
  set REDIS_URL=redis://localhost:6379/0
  python worker.py

In Docker Compose, a dedicated `worker` service runs this.
"""

from __future__ import annotations

import os

from rq import Worker  # type: ignore

from app.queue import get_queue, get_redis


def _start_anchor_poller() -> None:
    """Initialise the NonceManager + AnchorPoller for the anchor worker."""
    from web3 import Web3  # type: ignore

    from app.nonce_manager import NonceManager
    from app.anchor_poller import init_poller

    rpc_url = os.getenv("FLARE_RPC_URL", "https://flare-api.flare.network/ext/C/rpc")
    pk = os.getenv("ANCHOR_PRIVATE_KEY")
    if not pk:
        raise RuntimeError("ANCHOR_PRIVATE_KEY must be set for the anchor worker")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    acct = w3.eth.account.from_key(pk)

    nonce_mgr = NonceManager(w3, acct.address)
    poller = init_poller(nonce_manager=nonce_mgr)

    import logging
    logging.getLogger("middleware.worker").info(
        "anchor_worker_ready address=%s poller_pending=%s",
        acct.address, len(poller._pending),
    )


def main() -> None:
    queue_names = [q.strip() for q in (os.getenv("RQ_QUEUES") or "default").split(",") if q.strip()]
    queues = [get_queue(name) for name in queue_names]

    # If this is the anchor worker, start the confirmation poller
    if os.getenv("ANCHOR_WORKER", "").strip() in ("1", "true", "yes"):
        _start_anchor_poller()

    worker = Worker(queues, connection=get_redis())
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
