from __future__ import annotations

"""RQ jobs used by the API.

This file intentionally contains only job functions and small helpers.
The API enqueues these jobs and workers execute them out-of-process.

Design goals:
- No reliance on global env mutation
- Deterministic evidence generation (manifest is canonical)
- Idempotent-ish behavior where possible
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import anyio

from . import bundle, compliance, db, fx_providers, models, storage, vc  # type: ignore
from .config import get_config as load_config
from .iso_messages import camt054 as iso_camt054  # type: ignore
from .iso_messages import pacs002 as iso_pacs002  # type: ignore
from .iso_messages import pacs004 as iso_pacs004  # type: ignore
from .iso_messages import pain001 as iso_pain001  # type: ignore
from .iso_messages import pain002 as iso_pain002  # type: ignore
from .iso_messages import remt001 as iso_remt001  # type: ignore
from .sse import hub

import logging
import traceback

ARTIFACTS_DIR = os.getenv("ARTIFACTS_DIR", "artifacts")

logger = logging.getLogger("middleware.jobs")


def _ensure_dir_for_receipt(rid: str) -> Path:
    out = Path(ARTIFACTS_DIR) / rid
    out.mkdir(parents=True, exist_ok=True)
    return out


def _sha256_hex(b: bytes) -> str:
    import hashlib

    return "0x" + hashlib.sha256(b).hexdigest()


def _write_iso_artifact(session, receipt_id: str, type_str: str, filename: str, content: bytes) -> Tuple[str, str]:
    out_dir = _ensure_dir_for_receipt(receipt_id)
    file_path = out_dir / filename
    try:
        file_path.write_bytes(content)
    except Exception:
        # best-effort write; proceed to DB row
        pass
    sha = _sha256_hex(content)
    art = models.ISOArtifact(receipt_id=receipt_id, type=type_str, path=str(file_path), sha256=sha)
    session.add(art)
    session.commit()
    return str(file_path), sha


def _write_status_json(rec: models.Receipt) -> None:
    """Write current receipt status to status.json file.
    
    This provides an up-to-date status file that gets updated after anchoring,
    while evidence.zip remains immutable with the original snapshot.
    """
    try:
        out_dir = _ensure_dir_for_receipt(str(rec.id))
        status_file = out_dir / "status.json"
        
        status_data = {
            "receipt_id": str(rec.id),
            "status": rec.status,
            "bundle_hash": rec.bundle_hash,
            "flare_txid": rec.flare_txid,
            "anchored_at": rec.anchored_at.isoformat() if rec.anchored_at else None,
            "created_at": rec.created_at.isoformat() if rec.created_at else None,
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        status_file.write_text(
            json.dumps(status_data, indent=2, separators=(",", ": "), default=str)
        )
    except Exception as e:
        # Best-effort; log but don't fail the job
        logger.warning("Failed to write status.json for %s: %s", rec.id, str(e))


def _resolve_anchor_pk(cfg) -> Optional[str]:
    try:
        sec = getattr(cfg, "security", None)
        mode = getattr(sec, "anchor_mode", "managed") if sec else "managed"
        if mode == "self":
            return os.getenv("ANCHOR_PRIVATE_KEY")
        key_ref = getattr(sec, "key_ref", None) if sec else None
        if key_ref:
            if isinstance(key_ref, str) and key_ref.startswith("env:"):
                return os.getenv(key_ref.split(":", 1)[1])
            val = os.getenv(str(key_ref))
            if val:
                return val
            alt = f"KEYREF_{str(key_ref).upper()}"
            val2 = os.getenv(alt)
            if val2:
                return val2
        return os.getenv("ANCHOR_PRIVATE_KEY")
    except Exception:
        return os.getenv("ANCHOR_PRIVATE_KEY")




def _project_execution_mode(session, rec: models.Receipt) -> str:
    """Return per-project anchoring mode.

    Default: platform (middleware anchors).
    """

    try:
        if not getattr(rec, "project_id", None):
            return "platform"
        proj = session.get(models.Project, rec.project_id)
        if not proj or not getattr(proj, "config", None):
            return "platform"
        cfg = proj.config or {}
        anch = cfg.get("anchoring") or {}
        mode = anch.get("execution_mode") or "platform"
        return str(mode)
    except Exception:
        return "platform"


def _project_anchoring_chains(session, rec: models.Receipt) -> list[dict]:
    """Return per-project anchoring chains (list of dicts) if configured."""

    try:
        if not getattr(rec, "project_id", None):
            return []
        proj = session.get(models.Project, rec.project_id)
        if not proj or not getattr(proj, "config", None):
            return []
        cfg = proj.config or {}
        anch = cfg.get("anchoring") or {}
        chains = anch.get("chains") or []
        if isinstance(chains, list):
            out: list[dict] = []
            for c in chains:
                if isinstance(c, dict) and c.get("contract"):
                    out.append(c)
            return out
        return []
    except Exception:
        return []


def process_receipt_job(
    receipt_id: str,
    callback_url: Optional[str] = None,
    reason_code: Optional[str] = None,
    is_refund: bool = False,
) -> None:
    """Main background pipeline for a receipt.

    Runs in an RQ worker.
    
    Args:
        receipt_id: Receipt UUID
        callback_url: Optional callback URL to notify on completion
        reason_code: Optional reason code (for refunds/returns)
        is_refund: If True, generates pacs.004 instead of pain.001
    """

    session = db.SessionLocal()
    rec: Optional[models.Receipt] = None
    try:
        rec = session.get(models.Receipt, receipt_id)
        if not rec:
            return

        cfg = load_config(session)

        receipt_dict: Dict[str, Any] = {
            "id": str(rec.id),
            "reference": rec.reference,
            "tip_tx_hash": rec.tip_tx_hash,
            "chain": rec.chain,
            "amount": rec.amount,
            "currency": rec.currency,
            "sender_wallet": rec.sender_wallet,
            "receiver_wallet": rec.receiver_wallet,
            "status": rec.status,
            "created_at": rec.created_at,
        }

        # Compliance checks
        try:
            tr = compliance.evaluate_travel_rule(
                amount=receipt_dict.get("amount"),
                threshold=getattr(getattr(cfg, "compliance", None), "travel_rule_threshold", None),
                provider=getattr(getattr(cfg, "compliance", None), "travel_rule_provider", None),
            )
            sc = compliance.check_sanctions(
                sender_wallet=receipt_dict.get("sender_wallet"),
                receiver_wallet=receipt_dict.get("receiver_wallet"),
                provider=getattr(getattr(cfg, "compliance", None), "sanctions_provider", None),
                metadata={"reference": receipt_dict.get("reference")},
            )
            comp = {
                "travel_rule": {"decision": tr.decision, "reason": tr.reason},
                "sanctions": {"decision": sc.decision, "reason": sc.reason},
            }
            _write_iso_artifact(
                session,
                str(rec.id),
                "compliance",
                "compliance.json",
                json.dumps(comp, separators=(",", ":"), default=str).encode("utf-8"),
            )

            enforce_tr = getattr(getattr(cfg, "compliance", None), "travel_rule_enforce", False)
            enforce_sc = getattr(getattr(cfg, "compliance", None), "sanctions_enforce", False)
            if (enforce_tr and getattr(tr, "decision", "allow") == "deny") or (
                enforce_sc and getattr(sc, "decision", "allow") == "deny"
            ):
                rec.status = "failed"
                session.commit()
                return
        except Exception:
            pass

        # FX enrichment helper artifact
        try:
            fxp = getattr(getattr(cfg, "fx_policy", None), "provider", None)
            mode = getattr(getattr(cfg, "fx_policy", None), "mode", "none")
            if fxp and mode != "none":
                base = getattr(getattr(cfg, "fx_policy", None), "base_ccy", None)
                ccy = receipt_dict.get("currency")
                feed = getattr(getattr(cfg, "fx_policy", None), "chainlink_feed", None)
                rpc = getattr(getattr(cfg, "fx_policy", None), "chainlink_rpc_url", None) or getattr(
                    getattr(cfg, "ledger", None), "rpc_url", None
                )
                detail = fx_providers.get_rate_detail(base_ccy=base, quote_ccy=ccy, provider=fxp, rpc_url=rpc, feed=feed)
                fx_info = {
                    "base_ccy": base,
                    "quote_ccy": ccy,
                    "provider": fxp,
                    "rate": detail.get("rate"),
                    "source": detail.get("source"),
                    "ts": datetime.utcnow().isoformat(),
                }
                _write_iso_artifact(
                    session,
                    str(rec.id),
                    "fx",
                    "fx.json",
                    json.dumps(fx_info, separators=(",", ":"), default=str).encode("utf-8"),
                )
        except Exception:
            pass

        # ISO generation - pain.001 for normal payments, pacs.004 for refunds
        if is_refund:
            # Load original receipt for pacs.004 generation
            original_rec = None
            if rec.refund_of:
                original_rec = session.get(models.Receipt, rec.refund_of)
            
            if original_rec:
                original_dict = {
                    "id": str(original_rec.id),
                    "reference": original_rec.reference,
                    "tip_tx_hash": original_rec.tip_tx_hash,
                    "chain": original_rec.chain,
                    "amount": original_rec.amount,
                    "currency": original_rec.currency,
                    "sender_wallet": original_rec.sender_wallet,
                    "receiver_wallet": original_rec.receiver_wallet,
                    "created_at": original_rec.created_at,
                }
                xml_bytes = iso_pacs004.generate_pacs004(
                    original_dict,
                    refund_id=str(rec.id),
                    reason_code=reason_code
                )
                _write_iso_artifact(session, str(rec.id), "pacs.004", "pacs004.xml", xml_bytes)
            else:
                # Fallback if original not found
                xml_bytes = iso_pain001.generate_pain001_with_fx(receipt_dict, cfg)
                _write_iso_artifact(session, str(rec.id), "pain.001", "pain001.xml", xml_bytes)
        else:
            xml_bytes = iso_pain001.generate_pain001_with_fx(receipt_dict, cfg)
            _write_iso_artifact(session, str(rec.id), "pain.001", "pain001.xml", xml_bytes)

        # Optional remittance
        try:
            if getattr(getattr(cfg, "mapping", None), "structured_remittance", False):
                rmt_bytes = iso_remt001.generate_remt001(receipt_dict)
                _write_iso_artifact(session, str(rec.id), "remt.001", "remt001.xml", rmt_bytes)
        except Exception:
            pass

        # Create deterministic evidence bundle (and manifest signature)
        zip_path, bundle_hash = bundle.create_bundle(receipt_dict, xml_bytes)
        rec.bundle_hash = bundle_hash
        session.commit()

        # Optional storage upload (IPFS/Arweave)
        try:
            store_mode = getattr(getattr(cfg, "evidence", None), "store", None)
            mode = getattr(store_mode, "mode", "local") if store_mode else "local"
            if mode in ("ipfs", "arweave"):
                identifier, _ = storage.upload_bundle(zip_path, mode)
                if identifier:
                    storage.save_storage_metadata(_ensure_dir_for_receipt(str(rec.id)), identifier, mode)
        except Exception:
            pass

        # Optional VC issuance
        try:
            vc_obj = vc.issue_vc(bundle_hash, {"id": str(rec.id), "reference": rec.reference, "status": rec.status})
            _write_iso_artifact(
                session,
                str(rec.id),
                "vc",
                "vc.json",
                json.dumps(vc_obj, separators=(",", ":"), default=str).encode("utf-8"),
            )
        except Exception:
            pass

        anchored = False

        # Tenant mode: stop after evidence generation, wait for tenant to confirm anchoring
        exec_mode = _project_execution_mode(session, rec)
        if exec_mode == "tenant":
            rec.status = "awaiting_anchor"
            session.commit()
            # SSE notify
            try:
                evt_payload = {
                    "receipt_id": str(rec.id),
                    "status": rec.status,
                    "bundle_hash": rec.bundle_hash,
                    "flare_txid": rec.flare_txid,
                    "xml_url": f"/files/{rec.id}/pain001.xml",
                    "bundle_url": f"/files/{rec.id}/evidence.zip",
                    "created_at": rec.created_at.isoformat() if rec.created_at else None,
                    "anchored_at": rec.anchored_at.isoformat() if rec.anchored_at else None,
                }
                anyio.from_thread.run(hub.publish, str(rec.id), evt_payload)  # type: ignore
            except Exception:
                pass
            return

        # Platform mode anchoring:
        # - Prefer per-project chains (project override) when present
        # - Else fall back to org config chains
        proj_chains = _project_anchoring_chains(session, rec)
        org_chains = list(getattr(getattr(cfg, "anchoring", None), "chains", []) or [])

        chains_src: list[dict] = []
        if proj_chains:
            chains_src = proj_chains
        elif org_chains:
            for ch in org_chains:
                chains_src.append(
                    {
                        "name": getattr(ch, "name", None),
                        "contract": getattr(ch, "contract", None),
                        "rpc_url": getattr(ch, "rpc_url", None),
                        "explorer_base_url": getattr(ch, "explorer_base_url", None),
                    }
                )

        if not chains_src:
            # Last resort (keeps backwards compatibility)
            chains_src = [
                {
                    "name": rec.chain or "flare",
                    "contract": os.getenv("ANCHOR_CONTRACT_ADDR") or "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
                    "rpc_url": os.getenv("FLARE_RPC_URL"),
                }
            ]

        successes = 0
        pk = _resolve_anchor_pk(cfg)

        from . import anchor as anchor_py  # type: ignore

        logger.info(
            "anchoring_start rid=%s exec_mode=%s chain=%s pk_set=%s chains=%s",
            str(rec.id),
            exec_mode,
            rec.chain,
            bool(pk),
            [c.get("name") for c in chains_src if isinstance(c, dict)],
        )


        last_anchor_err: Optional[str] = None

        for ch in chains_src:
            chain_name = (ch.get("name") if isinstance(ch, dict) else None) or "unknown"
            rpc_url = (
                (ch.get("rpc_url") if isinstance(ch, dict) else None)
                or getattr(getattr(cfg, "ledger", None), "rpc_url", None)
                or os.getenv("FLARE_RPC_URL")
            )
            contract_addr = (
                (ch.get("contract") if isinstance(ch, dict) else None)
                or os.getenv("ANCHOR_CONTRACT_ADDR")
                or "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8"
            )

            try:
                logger.info(
                    "anchoring_try rid=%s chain=%s rpc=%s contract=%s pk_set=%s bundle_hash=%s",
                    str(rec.id),
                    str(chain_name),
                    str(rpc_url),
                    str(contract_addr),
                    bool(pk),
                    str(bundle_hash),
                )

                txid, block_no = anchor_py.anchor_bundle(
                    bundle_hash,
                    rpc_url=rpc_url,
                    contract_addr=contract_addr,
                    private_key=pk,
                    abi_path=os.getenv("ANCHOR_ABI_PATH"),
                    lookback_blocks=int(os.getenv("ANCHOR_LOOKBACK_BLOCKS", "50000")),
                )

                now = datetime.utcnow()

                if not rec.flare_txid:
                    rec.flare_txid = txid
                if not rec.anchored_at:
                    rec.anchored_at = now

                session.add(models.ChainAnchor(receipt_id=str(rec.id), chain=str(chain_name), txid=txid, anchored_at=now))
                session.commit()

                logger.info(
                    "anchoring_success rid=%s chain=%s txid=%s block=%s",
                    str(rec.id),
                    str(chain_name),
                    str(txid),
                    str(block_no),
                )

                successes += 1

            except Exception as e:
                session.rollback()

                last_anchor_err = f"{type(e).__name__}: {str(e)[:500]}"
                logger.error(
                    "anchoring_failed rid=%s chain=%s err=%s",
                    str(rec.id),
                    str(chain_name),
                    last_anchor_err,
                )
                logger.debug("anchoring_failed_trace rid=%s trace=%s", str(rec.id), traceback.format_exc())


        if successes > 0:
            rec.status = "anchored"
            session.commit()
            anchored = True
            # Write current status to status.json
            _write_status_json(rec)
        else:
            rec.status = "failed"
            session.commit()
            # Write current status to status.json
            _write_status_json(rec)

        try:
            if last_anchor_err:
                if hasattr(rec, "last_error"):
                    rec.last_error = f"anchor:{last_anchor_err}"
                elif hasattr(rec, "error"):
                    rec.error = f"anchor:{last_anchor_err}"
        except Exception:
            pass

        # Status/extra ISO artifacts
        try:
            payload2 = {
                "id": str(rec.id),
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
            p002_bytes = iso_pain002.generate_pain002(payload2)
            _write_iso_artifact(session, str(rec.id), "pain.002", "pain002.xml", p002_bytes)
            if getattr(getattr(cfg, "status", None), "emit_pacs002", False):
                try:
                    p2i = iso_pacs002.generate_pacs002(payload2)
                    _write_iso_artifact(session, str(rec.id), "pacs.002", "pacs002.xml", p2i)
                except Exception:
                    pass
            if anchored:
                c054_bytes = iso_camt054.generate_camt054(payload2)
                _write_iso_artifact(session, str(rec.id), "camt.054", "camt054.xml", c054_bytes)
        except Exception:
            pass

        # Persist primary artifact paths
        rec.xml_path = f"{ARTIFACTS_DIR}/{rec.id}/pain001.xml"
        rec.bundle_path = f"{ARTIFACTS_DIR}/{rec.id}/evidence.zip"
        session.commit()

        # SSE notify (best-effort)
        try:
            evt_payload = {
                "receipt_id": str(rec.id),
                "status": rec.status,
                "bundle_hash": rec.bundle_hash,
                "flare_txid": rec.flare_txid,
                "xml_url": f"/files/{rec.id}/pain001.xml",
                "bundle_url": f"/files/{rec.id}/evidence.zip",
                "created_at": rec.created_at.isoformat() if rec.created_at else None,
                "anchored_at": rec.anchored_at.isoformat() if rec.anchored_at else None,
            }
            anyio.from_thread.run(hub.publish, str(rec.id), evt_payload)  # type: ignore
        except Exception:
            pass

        # Optional callback
        if callback_url:
            try:
                import requests

                cb_payload = {
                    "receipt_id": str(rec.id),
                    "status": rec.status,
                    "bundle_hash": rec.bundle_hash,
                    "flare_txid": rec.flare_txid,
                    "xml_url": f"/files/{rec.id}/pain001.xml",
                    "bundle_url": f"/files/{rec.id}/evidence.zip",
                    "created_at": rec.created_at.isoformat() if rec.created_at else None,
                    "anchored_at": rec.anchored_at.isoformat() if rec.anchored_at else None,
                }
                base_url = os.getenv("PUBLIC_BASE_URL")
                if base_url:
                    cb_payload["xml_url"] = f"{base_url}{cb_payload['xml_url']}"
                    cb_payload["bundle_url"] = f"{base_url}{cb_payload['bundle_url']}"
                requests.post(callback_url, json=cb_payload, timeout=15)
            except Exception:
                pass

    except Exception:
        if rec is not None:
            try:
                rec.status = "failed"
                session.commit()
            except Exception:
                pass
        raise
    finally:
        session.close()
