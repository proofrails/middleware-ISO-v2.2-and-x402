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


def main() -> None:
    queue_names = [q.strip() for q in (os.getenv("RQ_QUEUES") or "default").split(",") if q.strip()]
    queues = [get_queue(name) for name in queue_names]
    worker = Worker(queues, connection=get_redis())
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
