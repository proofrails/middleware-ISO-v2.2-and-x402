from __future__ import annotations

import os
from datetime import datetime
from urllib.parse import urlparse

from fastapi import HTTPException, Request

from app import models

try:
    from eth_account import Account  # type: ignore
    from eth_account.messages import encode_defunct  # type: ignore
except Exception:  # pragma: no cover
    Account = None  # type: ignore
    encode_defunct = None  # type: ignore


def expected_domain(request: Request) -> str:
    """Return the expected SIWE domain.

    Uses PUBLIC_BASE_URL when set, else uses request Host header.
    """

    base = os.getenv("PUBLIC_BASE_URL")
    if base:
        return urlparse(base).netloc or urlparse(base).hostname or base
    return request.headers.get("host") or (request.url.hostname or "localhost")


def verify_siwe_message(message: str, signature: str, *, expected: str, nonces: dict[str, datetime], session) -> dict:
    """Verify a SIWE (EIP-4361) message/signature.

    Returns: { linked: bool, address: str, domain: str, chainId: str | None }
    """

    if Account is None or encode_defunct is None:
        raise HTTPException(status_code=501, detail="siwe_verification_unavailable")

    lines = [l.strip("\r") for l in message.split("\n")]
    if len(lines) < 2 or "wants you to sign in with your Ethereum account:" not in lines[0]:
        raise HTTPException(status_code=400, detail="invalid_siwe_format")

    domain = lines[0].split(" wants you to sign in with your Ethereum account:", 1)[0]
    address = lines[1].strip()

    fields = {}
    for ln in lines[2:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            fields[k.strip().lower()] = v.strip()

    nonce = fields.get("nonce")
    chain_id_str = fields.get("chain id") or fields.get("chainid")

    if not nonce or nonce not in nonces:
        raise HTTPException(status_code=400, detail="invalid_nonce")

    if domain != expected:
        raise HTTPException(status_code=400, detail="domain_mismatch")

    # Recover address
    msg = encode_defunct(text=message)
    recovered = Account.recover_message(msg, signature=signature)
    if not isinstance(recovered, str):
        raise HTTPException(status_code=400, detail="recover_failed")
    if recovered.lower() != str(address).lower():
        raise HTTPException(status_code=400, detail="address_mismatch")

    # consume nonce
    try:
        nonces.pop(nonce, None)
    except Exception:
        pass

    # store linked wallet best-effort
    try:
        exists = session.query(models.LinkedWallet).filter(models.LinkedWallet.address == recovered).first()
        if not exists:
            session.add(models.LinkedWallet(address=recovered))
            session.commit()
    except Exception:
        session.rollback()

    return {"linked": True, "address": recovered, "domain": domain, "chainId": chain_id_str}


def legacy_verify(address: str, nonce: str, signature: str, *, nonces: dict[str, datetime], session) -> dict:
    ok = bool(address and nonce and signature and nonce in nonces)
    if ok:
        try:
            nonces.pop(nonce, None)
        except Exception:
            pass
        try:
            exists = session.query(models.LinkedWallet).filter(models.LinkedWallet.address == address).first()
            if not exists:
                session.add(models.LinkedWallet(address=address))
                session.commit()
        except Exception:
            session.rollback()
    return {"linked": ok, "address": address, "note": "legacy-noop-verification"}
