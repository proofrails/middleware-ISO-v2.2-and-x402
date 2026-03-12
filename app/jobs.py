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

        # Tenant mode: stop after evidence generation, wait for tenant to confirm anchoring
        exec_mode = _project_execution_mode(session, rec)
        if exec_mode == "tenant":
            rec.status = "awaiting_anchor"
            session.commit()
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

        # Platform mode: resolve chain config, then enqueue to anchor queue
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
            chains_src = [
                {
                    "name": rec.chain or "flare",
                    "contract": os.getenv("ANCHOR_CONTRACT_ADDR") or "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
                    "rpc_url": os.getenv("FLARE_RPC_URL"),
                }
            ]

        pk = _resolve_anchor_pk(cfg)

        # Persist artifact paths now (before anchor)
        rec.xml_path = f"{ARTIFACTS_DIR}/{rec.id}/pain001.xml"
        rec.bundle_path = f"{ARTIFACTS_DIR}/{rec.id}/evidence.zip"
        rec.status = "awaiting_anchor"
        session.commit()

        logger.info(
            "prep_done rid=%s enqueuing_anchor chains=%s",
            str(rec.id),
            [c.get("name") for c in chains_src if isinstance(c, dict)],
        )

        # Enqueue to anchor queue for fire-and-forget sending
        from .queue import get_queue
        anchor_q = get_queue("anchor")
        anchor_q.enqueue(
            anchor_receipt_job,
            receipt_id=str(rec.id),
            bundle_hash=bundle_hash,
            chains=chains_src,
            private_key=pk,
            callback_url=callback_url,
            job_timeout=int(os.getenv("RQ_JOB_TIMEOUT", "600")),
        )

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


def anchor_receipt_job(
    receipt_id: str,
    bundle_hash: str,
    chains: list[dict],
    private_key: Optional[str] = None,
    callback_url: Optional[str] = None,
) -> None:
    """Send anchor transactions without waiting for confirmations.

    The AnchorPoller background thread handles confirmation polling.
    Runs on the 'anchor' queue processed by the anchor worker.
    """
    from . import anchor as anchor_py  # type: ignore
    from .anchor_poller import get_poller
    from .nonce_manager import NonceManager

    poller = get_poller()

    session = db.SessionLocal()
    try:
        rec = session.get(models.Receipt, receipt_id)
        if not rec:
            logger.warning("anchor_job_receipt_missing rid=%s", receipt_id)
            return

        pk = private_key or os.getenv("ANCHOR_PRIVATE_KEY")
        if not pk:
            rec.status = "failed"
            session.commit()
            raise RuntimeError("ANCHOR_PRIVATE_KEY is not set")

        for ch in chains:
            chain_name = (ch.get("name") if isinstance(ch, dict) else None) or "unknown"
            rpc_url = (
                (ch.get("rpc_url") if isinstance(ch, dict) else None)
                or os.getenv("FLARE_RPC_URL")
            )
            contract_addr = (
                (ch.get("contract") if isinstance(ch, dict) else None)
                or os.getenv("ANCHOR_CONTRACT_ADDR")
                or "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8"
            )

            try:
                # Get nonce from the anchor worker's NonceManager (if available)
                # Otherwise fall back to querying the chain
                from web3 import Web3  # type: ignore
                w3 = Web3(Web3.HTTPProvider(rpc_url or "https://flare-api.flare.network/ext/C/rpc"))
                acct = w3.eth.account.from_key(pk)

                # Use the global nonce manager if the poller has one, else query chain
                nonce_mgr = poller._nonce_manager if poller else None
                if nonce_mgr:
                    nonce = nonce_mgr.next()
                else:
                    nonce = w3.eth.get_transaction_count(acct.address, "pending")

                logger.info(
                    "anchor_send_start rid=%s chain=%s nonce=%s contract=%s",
                    receipt_id, chain_name, nonce, contract_addr,
                )

                txid, nonce_used = anchor_py.anchor_send(
                    bundle_hash,
                    nonce=nonce,
                    rpc_url=rpc_url,
                    contract_addr=contract_addr,
                    private_key=pk,
                    abi_path=os.getenv("ANCHOR_ABI_PATH"),
                )

                # Store tx hash on receipt so Provn sync can see it even before confirmation
                if not rec.flare_txid:
                    rec.flare_txid = txid
                session.commit()

                # Register with poller for async confirmation
                if poller:
                    poller.track(receipt_id, txid, chain_name, rpc_url=rpc_url)
                else:
                    # Fallback: no poller running, confirm synchronously
                    logger.warning("anchor_job_no_poller rid=%s falling_back_to_sync", receipt_id)
                    _sync_confirm_fallback(session, rec, txid, chain_name, rpc_url, callback_url)

                logger.info("anchor_send_done rid=%s txid=%s nonce=%s", receipt_id, txid, nonce_used)

            except Exception as e:
                session.rollback()
                # If send failed, nonce was NOT consumed — don't increment
                if nonce_mgr:
                    nonce_mgr.reset()
                logger.error(
                    "anchor_send_failed rid=%s chain=%s err=%s",
                    receipt_id, chain_name, repr(e),
                )
                logger.debug("anchor_send_failed_trace rid=%s trace=%s", receipt_id, traceback.format_exc())
                # Mark failed if this was the only/last chain
                rec.status = "failed"
                session.commit()

    except Exception:
        logger.exception("anchor_receipt_job_error rid=%s", receipt_id)
        raise
    finally:
        session.close()


def _sync_confirm_fallback(
    session, rec, txid: str, chain_name: str, rpc_url: Optional[str], callback_url: Optional[str]
) -> None:
    """Synchronous confirmation fallback when no AnchorPoller is running."""
    from . import anchor as anchor_py  # type: ignore
    from web3 import Web3  # type: ignore

    w3 = Web3(Web3.HTTPProvider(rpc_url or "https://flare-api.flare.network/ext/C/rpc"))
    receipt = w3.eth.wait_for_transaction_receipt(txid, timeout=180)

    status = int(receipt.get("status", 0) or 0)
    blk_no = int(receipt.get("blockNumber") or 0)

    if status == 1:
        now = datetime.utcnow()
        rec.status = "anchored"
        if not rec.anchored_at:
            rec.anchored_at = now
        session.add(models.ChainAnchor(receipt_id=str(rec.id), chain=chain_name, txid=txid, anchored_at=now))
        session.commit()
        finalize_receipt(str(rec.id), session=session, callback_url=callback_url)
    else:
        rec.status = "failed"
        session.commit()


def finalize_receipt(
    receipt_id: str,
    *,
    session=None,
    callback_url: Optional[str] = None,
) -> None:
    """Generate post-anchor ISO artifacts, SSE notify, and fire callback.

    Called by the AnchorPoller after a transaction is confirmed on-chain.
    """
    own_session = session is None
    if own_session:
        session = db.SessionLocal()

    try:
        rec = session.get(models.Receipt, receipt_id)
        if not rec:
            return

        cfg = load_config(session)

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
            if rec.status == "anchored":
                c054_bytes = iso_camt054.generate_camt054(payload2)
                _write_iso_artifact(session, str(rec.id), "camt.054", "camt054.xml", c054_bytes)
        except Exception:
            logger.debug("finalize_artifact_error rid=%s", receipt_id, exc_info=True)

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
        logger.exception("finalize_receipt_error rid=%s", receipt_id)
    finally:
        if own_session:
            session.close()
