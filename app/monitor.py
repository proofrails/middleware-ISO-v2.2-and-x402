"""Proactive monitoring loop for ISO middleware.

Runs three independent background tasks as daemon threads:

1. **Stale anchor recovery** (always on)
   Finds receipts stuck in ``awaiting_anchor`` with no ``flare_txid`` for
   longer than ``MONITOR_STALE_ANCHOR_MINUTES`` and re-enqueues them.

2. **Wallet watcher** (requires ``MONITOR_WALLET_WATCH_ENABLED=true``)
   Polls Flare C-Chain for new incoming transactions to every address in the
   ``watched_wallets`` table.  Unrecognised transfers are auto-converted to
   ISO receipts and queued for processing.

3. **FTSO price monitor** (always on when FTSO is enabled)
   Fetches all configured feed symbols every cycle and logs current prices.
   Surfaces as a ``GET /v1/monitor/ftso`` endpoint for dashboards.

4. **Scheduled batch reports** (requires ``MONITOR_BATCH_REPORTS_ENABLED=true``)
   On the first cycle of each new UTC day generates a camt.053 daily
   statement for all anchored receipts from the previous day.

Usage
-----
The monitor is started once in ``app_factory.create_app()``::

    from app.monitor import get_monitor
    get_monitor().start()

It is a singleton accessed via ``get_monitor()``.  Call ``stop()`` in
shutdown hooks if needed (it runs as a daemon thread so process exit also
cleans up automatically).

Environment variables
---------------------
``MONITOR_ENABLED``                  – Master switch (default: true)
``MONITOR_INTERVAL_SECONDS``         – Seconds between full cycles (default: 60)
``MONITOR_STALE_ANCHOR_MINUTES``     – Minutes before an anchor is retried (default: 10)
``MONITOR_WALLET_WATCH_ENABLED``     – Enable wallet watcher (default: false)
``MONITOR_BATCH_REPORTS_ENABLED``    – Enable daily camt.053 generation (default: false)
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("middleware.monitor")


# ── Status book-keeping ───────────────────────────────────────────────────────

@dataclass
class MonitorStatus:
    started_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    cycles_completed: int = 0
    stale_anchors_recovered: int = 0
    wallets_watched: int = 0
    new_receipts_auto_created: int = 0
    batch_reports_generated: int = 0
    last_ftso_rates: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "cycles_completed": self.cycles_completed,
            "stale_anchors_recovered": self.stale_anchors_recovered,
            "wallets_watched": self.wallets_watched,
            "new_receipts_auto_created": self.new_receipts_auto_created,
            "batch_reports_generated": self.batch_reports_generated,
            "last_ftso_rates": self.last_ftso_rates,
            "recent_errors": self.errors[-10:],
        }


# ── Monitor service ───────────────────────────────────────────────────────────

class MonitorService:
    """Singleton background monitor.  Start with ``start()``, stop with ``stop()``."""

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.status = MonitorStatus()
        self._last_report_date: Optional[str] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        from .settings import get_settings
        settings = get_settings()
        if not settings.monitor_enabled:
            logger.info("monitor_disabled via settings")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="iso-monitor",
        )
        self._thread.start()
        self.status.started_at = datetime.utcnow()
        logger.info("monitor_started interval=%ds", settings.monitor_interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        from .settings import get_settings
        settings = get_settings()
        interval = settings.monitor_interval_seconds

        # Stagger initial run slightly so app startup isn't impacted
        time.sleep(10)

        while not self._stop_event.wait(timeout=interval):
            try:
                self._run_cycle()
            except Exception as exc:
                msg = f"monitor_cycle_error: {exc}"
                logger.exception(msg)
                self.status.errors.append(msg)

    def _run_cycle(self) -> None:
        from .settings import get_settings
        settings = get_settings()

        logger.debug("monitor_cycle_start")

        self._recover_stale_anchors(settings)

        self._refresh_ftso_rates(settings)

        if settings.monitor_wallet_watch_enabled:
            self._watch_wallets(settings)

        if settings.monitor_batch_reports_enabled:
            self._maybe_generate_batch_reports()

        self.status.last_run_at = datetime.utcnow()
        self.status.cycles_completed += 1
        logger.debug("monitor_cycle_done cycle=%d", self.status.cycles_completed)

    # ── Task 1: Stale anchor recovery ─────────────────────────────────────────

    def _recover_stale_anchors(self, settings) -> None:
        """Re-enqueue receipts stuck in awaiting_anchor with no txid."""
        try:
            from . import db, models
            from .queue import get_queue

            cutoff = datetime.utcnow() - timedelta(minutes=settings.monitor_stale_anchor_minutes)
            session = db.SessionLocal()
            try:
                stale = (
                    session.query(models.Receipt)
                    .filter(
                        models.Receipt.status == "awaiting_anchor",
                        models.Receipt.flare_txid.is_(None),
                        models.Receipt.created_at < cutoff,
                    )
                    .limit(20)
                    .all()
                )

                if not stale:
                    return

                from .jobs import anchor_receipt_job
                import os

                q = get_queue("anchor")
                for rec in stale:
                    if not rec.bundle_hash:
                        logger.warning("stale_anchor_no_bundle rid=%s, skipping", rec.id)
                        continue

                    chain_name = rec.chain or "flare"
                    chains = [
                        {
                            "name": chain_name,
                            "contract": os.getenv(
                                "ANCHOR_CONTRACT_ADDR",
                                "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
                            ),
                            "rpc_url": os.getenv("FLARE_RPC_URL"),
                        }
                    ]
                    q.enqueue(
                        anchor_receipt_job,
                        receipt_id=str(rec.id),
                        bundle_hash=rec.bundle_hash,
                        chains=chains,
                        job_timeout=600,
                    )
                    self.status.stale_anchors_recovered += 1
                    logger.info(
                        "stale_anchor_requeued rid=%s age_min=%.1f",
                        rec.id,
                        (datetime.utcnow() - rec.created_at.replace(tzinfo=None)).total_seconds() / 60,
                    )
            finally:
                session.close()
        except Exception as exc:
            logger.debug("stale_anchor_recovery_error: %s", exc)

    # ── Task 2: FTSO price refresh ────────────────────────────────────────────

    def _refresh_ftso_rates(self, settings) -> None:
        """Fetch all known FTSO feeds and store in status for the API."""
        if not settings.ftso_enabled:
            return
        try:
            from .flare.ftso import get_ftso_rates, FEED_IDS

            feeds = list(FEED_IDS.keys())
            rates = get_ftso_rates(feeds)
            snapshot: Dict[str, Any] = {}
            for sym, rate in rates.items():
                if rate:
                    snapshot[sym] = {
                        "value": str(rate.value),
                        "timestamp": rate.timestamp,
                        "age_seconds": round(rate.age_seconds, 1),
                        "source": rate.source,
                    }
            if snapshot:
                self.status.last_ftso_rates = snapshot
                logger.debug("ftso_refresh feeds=%d", len(snapshot))
        except Exception as exc:
            logger.debug("ftso_refresh_error: %s", exc)

    # ── Task 3: Wallet watcher ────────────────────────────────────────────────

    def _watch_wallets(self, settings) -> None:
        """Check watched wallets for new incoming transactions on Flare."""
        try:
            from . import db, models
            from .queue import get_queue

            session = db.SessionLocal()
            try:
                wallets = (
                    session.query(models.WatchedWallet)
                    .filter(models.WatchedWallet.enabled == "true")
                    .all()
                )
                self.status.wallets_watched = len(wallets)

                if not wallets:
                    return

                try:
                    from web3 import Web3
                    rpc_url = settings.flare_rpc_url
                    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
                    current_block = w3.eth.block_number
                except Exception:
                    return

                for wallet in wallets:
                    try:
                        self._check_wallet(session, wallet, w3, current_block)
                    except Exception as exc:
                        logger.debug("wallet_watch_error addr=%s: %s", wallet.address, exc)

                session.commit()
            finally:
                session.close()
        except Exception as exc:
            logger.debug("wallet_watcher_error: %s", exc)

    def _check_wallet(self, session, wallet, w3, current_block: int) -> None:
        """Scan recent blocks for incoming transactions to one wallet."""
        from decimal import Decimal
        from . import models
        from .queue import enqueue_receipt_processing

        last_block_str = wallet.last_checked_block
        from_block = int(last_block_str, 16) + 1 if last_block_str else max(0, current_block - 50)

        if from_block > current_block:
            return

        # Scan at most 200 blocks per cycle to avoid RPC overload
        scan_to = min(current_block, from_block + 200)

        try:
            logs = w3.eth.get_logs({
                "fromBlock": from_block,
                "toBlock": scan_to,
                "topics": [
                    # No topic filter — check tx.to directly via getBlock
                    # We use a simpler approach: get all txs in range
                ],
            })
        except Exception:
            logs = []

        # Simpler path: iterate blocks (only viable for small ranges)
        new_txs = []
        for block_no in range(from_block, scan_to + 1):
            try:
                blk = w3.eth.get_block(block_no, full_transactions=True)
                for tx in blk.get("transactions", []):
                    to = (tx.get("to") or "").lower()
                    if to == wallet.address.lower() and tx.get("value", 0) > 0:
                        new_txs.append(tx)
            except Exception:
                continue

        for tx in new_txs:
            tx_hash = tx.get("hash", b"")
            if hasattr(tx_hash, "hex"):
                tx_hash = tx_hash.hex()
            else:
                tx_hash = str(tx_hash)

            # Skip if already recorded
            existing = (
                session.query(models.Receipt)
                .filter(models.Receipt.tip_tx_hash == tx_hash)
                .one_or_none()
            )
            if existing:
                continue

            value_flr = Decimal(tx.get("value", 0)) / Decimal(10 ** 18)
            if value_flr <= Decimal("0"):
                continue

            rid = uuid4()
            ref = f"monitor:flare:{tx_hash[:16]}"
            receipt = models.Receipt(
                id=rid,
                project_id=wallet.project_id,
                reference=ref,
                tip_tx_hash=tx_hash,
                chain="flare",
                amount=value_flr,
                currency="FLR",
                sender_wallet=(tx.get("from") or "unknown").lower(),
                receiver_wallet=wallet.address.lower(),
                status="pending",
                created_at=datetime.utcnow(),
            )
            session.add(receipt)
            session.flush()
            enqueue_receipt_processing(receipt_id=str(rid))
            self.status.new_receipts_auto_created += 1
            logger.info(
                "monitor_auto_receipt rid=%s wallet=%s tx=%s amount=%s FLR",
                rid,
                wallet.address,
                tx_hash,
                value_flr,
            )

        # Advance checkpoint
        wallet.last_checked_block = hex(scan_to)
        wallet.updated_at = datetime.utcnow()

    # ── Task 4: Daily batch reports ───────────────────────────────────────────

    def _maybe_generate_batch_reports(self) -> None:
        """Generate camt.053 statement for yesterday if not yet done today."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self._last_report_date == today:
            return

        try:
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            self._generate_daily_statement(yesterday)
            self._last_report_date = today
            self.status.batch_reports_generated += 1
            logger.info("batch_report_generated date=%s", yesterday)
        except Exception as exc:
            logger.debug("batch_report_error: %s", exc)

    def _generate_daily_statement(self, date_str: str) -> None:
        """Generate and persist a camt.053 statement for the given date."""
        from . import db, models
        from datetime import date as _date
        import os, json
        from pathlib import Path

        d = _date.fromisoformat(date_str)
        start = datetime(d.year, d.month, d.day, 0, 0, 0)
        end = datetime(d.year, d.month, d.day, 23, 59, 59)

        session = db.SessionLocal()
        try:
            receipts_q = (
                session.query(models.Receipt)
                .filter(
                    models.Receipt.status == "anchored",
                    models.Receipt.anchored_at >= start,
                    models.Receipt.anchored_at <= end,
                )
                .all()
            )
            receipt_dicts = [
                {
                    "id": str(r.id),
                    "reference": r.reference,
                    "tip_tx_hash": r.tip_tx_hash,
                    "chain": r.chain,
                    "amount": r.amount,
                    "currency": r.currency,
                    "sender_wallet": r.sender_wallet,
                    "receiver_wallet": r.receiver_wallet,
                    "status": r.status,
                    "created_at": r.created_at,
                    "anchored_at": r.anchored_at,
                    "flare_txid": r.flare_txid,
                    "bundle_hash": r.bundle_hash,
                }
                for r in receipts_q
            ]

            from .iso_messages.camt053 import generate_camt053
            xml_bytes = generate_camt053(date_str, receipt_dicts)

            out_dir = Path(os.getenv("ARTIFACTS_DIR", "artifacts")) / "statements"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"camt053_{date_str}.xml"
            out_path.write_bytes(xml_bytes)
            logger.info("camt053_written path=%s receipts=%d", out_path, len(receipt_dicts))
        finally:
            session.close()


# ── Singleton ─────────────────────────────────────────────────────────────────

_monitor: Optional[MonitorService] = None
_monitor_lock = threading.Lock()


def get_monitor() -> MonitorService:
    """Return the process-level singleton MonitorService."""
    global _monitor
    if _monitor is None:
        with _monitor_lock:
            if _monitor is None:
                _monitor = MonitorService()
    return _monitor
