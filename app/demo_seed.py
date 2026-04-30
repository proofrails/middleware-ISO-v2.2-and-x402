"""Demo data seeder.

Called once on startup when DEMO_MODE=true.
Creates a demo project and 15 realistic receipts with ISO artifacts.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

logger = logging.getLogger(__name__)

# Repeatable but varied demo data
_CHAINS = ["flare", "ethereum", "base"]
_CURRENCIES = {"flare": "FLR", "ethereum": "ETH", "base": "USDC"}
_WALLETS = [
    "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "0x8ba1f109551bD432803012645Ac136ddd64DBA72",
    "0xdD2FD4581271e230360230F9337D5c0430Bf44C0",
    "0xbDA5747bFD65F08deb54cb465eB87D40e51B197E",
    "0x2546BcD3c84621e976D8185a91A922aE77ECEc30",
    "0xFABB0ac9d68B0B445fB7357272Ff202C5651694a",
]
_REFERENCES = [
    "invoice-2026-001", "invoice-2026-002", "invoice-2026-003",
    "payment-Q1-042", "payment-Q1-043", "payment-Q1-044",
    "tip:creator:alice:7", "tip:creator:bob:12", "tip:creator:carol:3",
    "settlement-batch-091", "settlement-batch-092",
    "payout:march:ops:14", "payout:march:dev:22",
    "refund:inv-2025-998", "cross-border:EUR:tx55",
]


def _fake_txid(seed: str) -> str:
    return "0x" + hashlib.sha256(seed.encode()).hexdigest()


def _random_amount() -> Decimal:
    return Decimal(str(round(random.uniform(5, 5000), 2)))


def seed_demo_data(session) -> None:
    """Seed demo data if not already present."""
    from app import models
    from app.settings import get_settings

    settings = get_settings()

    # Check if already seeded
    existing = session.query(models.Project).filter(models.Project.name == "Demo Project").first()
    if existing:
        logger.info("demo_seed: already seeded, skipping")
        return

    logger.info("demo_seed: seeding demo data...")

    # 1. Create demo project
    project_id = uuid4()
    project = models.Project(
        id=project_id,
        name="Demo Project",
        owner_wallet="0xDemo0000000000000000000000000000000000000",
        config={"anchoring": {"execution_mode": "platform", "chains": [
            {"name": "flare", "contract": "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8"}
        ]}},
    )
    session.add(project)
    session.flush()

    artifacts_dir = Path(settings.artifacts_dir)
    now = datetime.now(timezone.utc)
    receipts_created = []

    for i, ref in enumerate(_REFERENCES):
        rid = uuid4()
        chain = _CHAINS[i % len(_CHAINS)]
        currency = _CURRENCIES[chain]
        amount = _random_amount()
        created_at = now - timedelta(days=random.uniform(0.1, 7), hours=random.uniform(0, 12))
        sender = random.choice(_WALLETS)
        receiver = random.choice([w for w in _WALLETS if w != sender])
        tx_hash = _fake_txid(f"tip-{ref}-{i}")

        # Determine status distribution: 10 anchored, 3 pending/awaiting, 2 failed
        if i < 10:
            status = "anchored"
        elif i < 13:
            status = random.choice(["pending", "awaiting_anchor"])
        else:
            status = "failed"

        rec = models.Receipt(
            id=rid,
            project_id=project_id,
            reference=ref,
            tip_tx_hash=tx_hash,
            chain=chain,
            amount=amount,
            currency=currency,
            sender_wallet=sender,
            receiver_wallet=receiver,
            status=status,
            created_at=created_at,
        )

        if status == "anchored":
            rec.anchored_at = created_at + timedelta(seconds=random.randint(8, 45))
            rec.flare_txid = _fake_txid(f"anchor-{ref}-{i}")

        session.add(rec)
        session.flush()

        # Generate real ISO artifacts for anchored receipts
        if status == "anchored":
            _generate_demo_artifacts(session, rec, artifacts_dir)

        receipts_created.append((str(rid), status))

    session.commit()
    logger.info("demo_seed: created %d receipts", len(receipts_created))


def _generate_demo_artifacts(session, rec, artifacts_dir: Path) -> None:
    """Generate pain001.xml, evidence.zip, and post-anchor artifacts for a demo receipt."""
    from app import models
    from app.iso_messages import pain001 as iso_pain001
    from app.iso_messages import pain002 as iso_pain002
    from app.iso_messages import camt054 as iso_camt054
    from app import bundle as bundle_mod
    from app.config import get_config

    rid = str(rec.id)
    out_dir = artifacts_dir / rid
    out_dir.mkdir(parents=True, exist_ok=True)

    receipt_dict: Dict[str, Any] = {
        "id": rid,
        "reference": rec.reference,
        "tip_tx_hash": rec.tip_tx_hash,
        "chain": rec.chain,
        "amount": rec.amount,
        "currency": rec.currency,
        "sender_wallet": rec.sender_wallet,
        "receiver_wallet": rec.receiver_wallet,
        "status": rec.status,
        "created_at": rec.created_at,
        "anchored_at": rec.anchored_at,
        "flare_txid": rec.flare_txid,
        "bundle_hash": rec.bundle_hash,
    }

    try:
        cfg = get_config(session)
    except Exception:
        # Fallback minimal config
        from app.config import OrgConfigModel, LedgerConfig, AssetDescriptor
        cfg = OrgConfigModel(
            ledger=LedgerConfig(network="flare", rpc_url="https://flare-api.flare.network/ext/C/rpc",
                                asset=AssetDescriptor(symbol="FLR", decimals=18)),
        )

    # pain.001
    try:
        xml_bytes = iso_pain001.generate_pain001_with_fx(receipt_dict, cfg)
    except Exception:
        from app import iso as iso_mod
        xml_bytes = iso_mod.generate_pain001(receipt_dict)

    _write_artifact(session, rid, "pain.001", "pain001.xml", xml_bytes, out_dir)

    # Evidence bundle
    try:
        zip_path, bundle_hash = bundle_mod.create_bundle(receipt_dict, xml_bytes)
        rec.bundle_hash = bundle_hash
        rec.bundle_path = str(zip_path)
        rec.xml_path = str(out_dir / "pain001.xml")
    except Exception as e:
        logger.debug("demo_seed: bundle creation failed for %s: %s", rid, e)
        # Create a fallback bundle_hash
        rec.bundle_hash = "0x" + hashlib.sha256(rid.encode()).hexdigest()

    # pain.002 (post-anchor)
    try:
        receipt_dict["bundle_hash"] = rec.bundle_hash
        receipt_dict["flare_txid"] = rec.flare_txid
        receipt_dict["status"] = rec.status
        p002_bytes = iso_pain002.generate_pain002(receipt_dict)
        _write_artifact(session, rid, "pain.002", "pain002.xml", p002_bytes, out_dir)
    except Exception:
        pass

    # camt.054 (notification)
    try:
        c054_bytes = iso_camt054.generate_camt054(receipt_dict)
        _write_artifact(session, rid, "camt.054", "camt054.xml", c054_bytes, out_dir)
    except Exception:
        pass

    # status.json
    try:
        status_data = {
            "receipt_id": rid,
            "status": rec.status,
            "bundle_hash": rec.bundle_hash,
            "flare_txid": rec.flare_txid,
            "anchored_at": rec.anchored_at.isoformat() if rec.anchored_at else None,
            "created_at": rec.created_at.isoformat() if rec.created_at else None,
            "last_updated": datetime.utcnow().isoformat(),
        }
        (out_dir / "status.json").write_text(json.dumps(status_data, indent=2, default=str))
    except Exception:
        pass

    # ChainAnchor row
    try:
        session.add(models.ChainAnchor(
            receipt_id=rid,
            chain=rec.chain or "flare",
            txid=rec.flare_txid,
            anchored_at=rec.anchored_at,
        ))
    except Exception:
        pass


def _write_artifact(session, receipt_id: str, type_str: str, filename: str, content: bytes, out_dir: Path) -> None:
    """Write artifact to disk and create DB record."""
    from app import models

    file_path = out_dir / filename
    try:
        file_path.write_bytes(content)
    except Exception:
        pass

    sha = "0x" + hashlib.sha256(content).hexdigest()
    art = models.ISOArtifact(receipt_id=receipt_id, type=type_str, path=str(file_path), sha256=sha)
    session.add(art)
