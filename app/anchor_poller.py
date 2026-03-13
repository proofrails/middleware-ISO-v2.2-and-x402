from __future__ import annotations

"""Background poller that confirms pending anchor transactions.

Runs as a daemon thread inside the anchor worker process.
Polls for tx receipts and finalises confirmed receipts.
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from . import anchor as anchor_py
from . import db, models
from .nonce_manager import NonceManager

logger = logging.getLogger("middleware.anchor_poller")

POLL_INTERVAL = float(os.getenv("ANCHOR_POLL_INTERVAL", "3"))
CONFIRM_TIMEOUT = float(os.getenv("ANCHOR_CONFIRM_TIMEOUT", "180"))


class _PendingTx:
    __slots__ = ("receipt_id", "tx_hash", "chain_name", "sent_at", "rpc_url")

    def __init__(self, receipt_id: str, tx_hash: str, chain_name: str, sent_at: float, rpc_url: str | None = None):
        self.receipt_id = receipt_id
        self.tx_hash = tx_hash
        self.chain_name = chain_name
        self.sent_at = sent_at
        self.rpc_url = rpc_url


class AnchorPoller:
    """Polls for on-chain confirmations and finalises receipts."""

    def __init__(self, nonce_manager: NonceManager | None = None):
        self._pending: list[_PendingTx] = []
        self._lock = threading.Lock()
        self._nonce_manager = nonce_manager
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- public API (called from anchor jobs) --

    def track(self, receipt_id: str, tx_hash: str, chain_name: str, rpc_url: str | None = None) -> None:
        with self._lock:
            self._pending.append(_PendingTx(
                receipt_id=receipt_id,
                tx_hash=tx_hash,
                chain_name=chain_name,
                sent_at=time.monotonic(),
                rpc_url=rpc_url,
            ))
        logger.info("poller_track rid=%s tx=%s chain=%s", receipt_id, tx_hash, chain_name)

    # -- lifecycle --

    def start(self) -> None:
        self._recover_from_db()
        self._thread = threading.Thread(target=self._run, daemon=True, name="anchor-poller")
        self._thread.start()
        logger.info("poller_started pending=%s", len(self._pending))

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    # -- internals --

    def _recover_from_db(self) -> None:
        """On startup, load receipts stuck in awaiting_anchor with a flare_txid."""
        session = db.SessionLocal()
        try:
            rows = (
                session.query(models.Receipt)
                .filter(
                    models.Receipt.status == "awaiting_anchor",
                    models.Receipt.flare_txid.isnot(None),
                )
                .all()
            )
            for r in rows:
                rpc_url = os.getenv("FLARE_RPC_URL")
                self._pending.append(_PendingTx(
                    receipt_id=str(r.id),
                    tx_hash=r.flare_txid,
                    chain_name=r.chain or "flare",
                    sent_at=time.monotonic(),
                    rpc_url=rpc_url,
                ))
            if rows:
                logger.info("poller_recovered count=%s", len(rows))
        finally:
            session.close()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._poll_once()
            except Exception:
                logger.exception("poller_poll_error")
            self._stop.wait(POLL_INTERVAL)

    def _pick_up_new_from_db(self) -> None:
        """Pick up any awaiting_anchor receipts added since startup (handles fork-after-thread issue)."""
        with self._lock:
            tracked_ids = {p.receipt_id for p in self._pending}

        session = db.SessionLocal()
        try:
            rows = (
                session.query(models.Receipt)
                .filter(
                    models.Receipt.status == "awaiting_anchor",
                    models.Receipt.flare_txid.isnot(None),
                )
                .all()
            )
            for r in rows:
                rid = str(r.id)
                if rid not in tracked_ids:
                    rpc_url = os.getenv("FLARE_RPC_URL")
                    with self._lock:
                        self._pending.append(_PendingTx(
                            receipt_id=rid,
                            tx_hash=r.flare_txid,
                            chain_name=r.chain or "flare",
                            sent_at=time.monotonic(),
                            rpc_url=rpc_url,
                        ))
                    logger.info("poller_pickup rid=%s tx=%s", rid, r.flare_txid)
        finally:
            session.close()

    def _poll_once(self) -> None:
        self._pick_up_new_from_db()
        with self._lock:
            snapshot = list(self._pending)
        if not snapshot:
            return

        done_ids: set[str] = set()

        for ptx in snapshot:
            try:
                result = anchor_py.anchor_confirm(ptx.tx_hash, rpc_url=ptx.rpc_url)
            except Exception:
                logger.debug("poller_confirm_error rid=%s tx=%s", ptx.receipt_id, ptx.tx_hash, exc_info=True)
                result = None

            if result is not None:
                success, status_int, blk_no = result
                if success:
                    self._finalise(ptx, blk_no)
                else:
                    self._mark_failed(ptx, f"tx reverted status={status_int}")
                done_ids.add(ptx.receipt_id)
            elif (time.monotonic() - ptx.sent_at) > CONFIRM_TIMEOUT:
                self._mark_failed(ptx, "confirmation timeout")
                if self._nonce_manager:
                    self._nonce_manager.reset()
                done_ids.add(ptx.receipt_id)

        if done_ids:
            with self._lock:
                self._pending = [p for p in self._pending if p.receipt_id not in done_ids]

    def _finalise(self, ptx: _PendingTx, blk_no: int) -> None:
        session = db.SessionLocal()
        try:
            rec: Optional[models.Receipt] = session.get(models.Receipt, ptx.receipt_id)
            if not rec:
                return

            now = datetime.now(timezone.utc)
            rec.status = "anchored"
            if not rec.anchored_at:
                rec.anchored_at = now

            session.add(models.ChainAnchor(
                receipt_id=str(rec.id), chain=ptx.chain_name, txid=ptx.tx_hash, anchored_at=now,
            ))
            session.commit()

            logger.info("poller_anchored rid=%s tx=%s block=%s", ptx.receipt_id, ptx.tx_hash, blk_no)

            # Generate post-anchor artifacts (best-effort)
            try:
                from .jobs import finalize_receipt
                finalize_receipt(str(rec.id), session=session)
            except Exception:
                logger.exception("poller_finalize_error rid=%s", ptx.receipt_id)

        except Exception:
            session.rollback()
            logger.exception("poller_finalise_error rid=%s", ptx.receipt_id)
        finally:
            session.close()

    def _mark_failed(self, ptx: _PendingTx, reason: str) -> None:
        session = db.SessionLocal()
        try:
            rec: Optional[models.Receipt] = session.get(models.Receipt, ptx.receipt_id)
            if not rec:
                return
            rec.status = "failed"
            session.commit()
            logger.warning("poller_failed rid=%s tx=%s reason=%s", ptx.receipt_id, ptx.tx_hash, reason)
        except Exception:
            session.rollback()
            logger.exception("poller_mark_failed_error rid=%s", ptx.receipt_id)
        finally:
            session.close()


# Module-level singleton (initialised by anchor worker on startup)
_poller: AnchorPoller | None = None


def get_poller() -> AnchorPoller | None:
    return _poller


def init_poller(nonce_manager: NonceManager | None = None) -> AnchorPoller:
    global _poller
    _poller = AnchorPoller(nonce_manager=nonce_manager)
    _poller.start()
    return _poller
