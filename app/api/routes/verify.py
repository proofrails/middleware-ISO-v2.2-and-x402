from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path
from typing import List

import requests
from fastapi import APIRouter, HTTPException

from app import schemas

router = APIRouter(tags=["verify"])

ARTIFACTS_DIR = os.getenv("ARTIFACTS_DIR", "artifacts")


def _fetch_cid_bytes(cid: str, store: str | None = None) -> bytes | None:
    try:
        s = (store or "").lower().strip()
        if not s:
            s = "ipfs" if cid.startswith("Qm") or cid.startswith("bafy") else "arweave"
        if s == "ipfs":
            gw = os.getenv("IPFS_GATEWAY", "https://ipfs.io/ipfs/")
            url = gw.rstrip("/") + "/" + cid
        else:
            gw = os.getenv("ARWEAVE_GATEWAY", "https://arweave.net/")
            url = gw.rstrip("/") + "/" + cid
        r = requests.get(url, timeout=30)
        if r.ok:
            return r.content
    except Exception:
        pass
    return None


@router.post("/v1/iso/verify", response_model=schemas.VerifyResponse)
def verify(req: schemas.VerifyRequest):
    errors: List[str] = []

    if not (req.bundle_hash or req.bundle_url):
        raise HTTPException(status_code=400, detail="Provide either bundle_url or bundle_hash")

    bundle_hash = req.bundle_hash
    if not bundle_hash and req.bundle_url:
        from app import bundle

        verification = bundle.verify_bundle(req.bundle_url)
        bundle_hash = verification.bundle_hash
        errors = list(verification.errors)

    matches = False
    txid = None
    anchored_at = None
    try:
        from app import anchor

        info = anchor.find_anchor(bundle_hash)
        matches = info.matches
        txid = info.txid
        anchored_at = info.anchored_at
    except Exception:
        try:
            from app import anchor_node

            info = anchor_node.find_anchor(bundle_hash)
            matches = info.matches
            txid = info.txid
            anchored_at = info.anchored_at
        except Exception:
            errors.append("anchor_lookup_unavailable")

    return schemas.VerifyResponse(
        matches_onchain=matches, bundle_hash=bundle_hash, flare_txid=txid, anchored_at=anchored_at, errors=errors
    )


@router.post("/v1/iso/verify-cid", response_model=schemas.VerifyResponse)
def verify_cid(req: schemas.VerifyCidRequest):
    content = _fetch_cid_bytes(req.cid, req.store)
    if not content:
        raise HTTPException(status_code=404, detail="cid_not_found")

    bundle_hash = "0x" + sha256(content).hexdigest()

    errors: List[str] = []
    matches = False
    txid = None
    anchored_at = None
    try:
        from app import anchor

        info = anchor.find_anchor(bundle_hash)
        matches = info.matches
        txid = info.txid
        anchored_at = info.anchored_at
    except Exception:
        try:
            from app import anchor_node

            info = anchor_node.find_anchor(bundle_hash)
            matches = info.matches
            txid = info.txid
            anchored_at = info.anchored_at
        except Exception:
            errors.append("anchor_lookup_unavailable")

    # optional VC hints
    vc_present = None
    vc_url = None
    arweave_txid = None
    issuer = None
    checksums = {"content_sha256": bundle_hash, "bundle_sha256": bundle_hash, "zip_size_bytes": len(content)}

    try:
        rid = req.receipt_id
        if rid:
            vc_path = Path(ARTIFACTS_DIR) / rid / "vc.json"
            if vc_path.exists():
                vc_present = True
                vc_url = f"/files/{rid}/vc.json"
                txt = vc_path.read_text(encoding="utf-8")
                vc_data = json.loads(txt)
                poss_issuer = vc_data.get("issuer")
                if isinstance(poss_issuer, dict):
                    issuer = poss_issuer.get("id") or poss_issuer.get("name")
                elif isinstance(poss_issuer, str):
                    issuer = poss_issuer
                checksums["vc_sha256"] = "0x" + sha256(txt.encode("utf-8")).hexdigest()
            else:
                vc_present = False
            ar_path = Path(ARTIFACTS_DIR) / rid / "arweave_txid.txt"
            if ar_path.exists():
                arweave_txid = ar_path.read_text().strip()
    except Exception:
        pass

    return schemas.VerifyResponse(
        matches_onchain=matches,
        bundle_hash=bundle_hash,
        flare_txid=txid,
        anchored_at=anchored_at,
        vc_present=vc_present,
        vc_url=vc_url,
        arweave_txid=arweave_txid,
        issuer=issuer,
        checksums=checksums,
        errors=errors,
    )
