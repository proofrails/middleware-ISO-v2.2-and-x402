from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Minimal VC issuance helper.
# Tries to create a JWS-like envelope for the bundle_hash bound to a receipt.
# If Ed25519 (PyNaCl) is unavailable, falls back to an unsigned envelope with alg='none'.


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_ed25519_key() -> Optional[Any]:
    try:
        from nacl.signing import SigningKey  # type: ignore
    except Exception:
        return None
    key_hex = os.getenv("VC_PRIVATE_KEY")  # 64 hex characters for Ed25519 private key (seed)
    if not key_hex:
        return None
    try:
        key_bytes = bytes.fromhex(key_hex.replace("0x", ""))
        if len(key_bytes) != 32:
            # Support 64-byte private key format where first half is seed
            if len(key_bytes) == 64:
                key_bytes = key_bytes[:32]
            else:
                return None
        return SigningKey(key_bytes)
    except Exception:
        return None


def _did_key_from_public(pubkey: bytes) -> str:
    # did:key for ed25519 = multicodec 0xED 0x01 + pubkey (32 bytes) then multibase base58btc "z"
    try:
        import base58  # type: ignore
    except Exception:
        return "did:key:dev"
    multicodec = b"\xed\x01" + pubkey
    multibase = "z" + base58.b58encode(multicodec).decode("ascii")
    return f"did:key:{multibase}"


def issue_vc(bundle_hash: str, receipt: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a minimal W3C VC-like JSON with a JWS envelope:
      - vc.credentialSubject.bundle_hash = 0x...
      - vc.credentialSubject.receipt_id = <uuid>
      - proof.jws with alg EdDSA when Ed25519 key present, else alg 'none'
    """
    # Payload
    vc = {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
        ],
        "type": ["VerifiableCredential"],
        "issuer": "did:key:dev",
        "issuanceDate": _now_iso(),
        "credentialSubject": {
            "bundle_hash": bundle_hash,
            "receipt_id": receipt.get("id"),
            "reference": receipt.get("reference"),
            "status": receipt.get("status"),
        },
    }

    # Try Ed25519 signing
    signer = _load_ed25519_key()
    if signer is not None:
        try:
            pub = signer.verify_key.encode()
            did = _did_key_from_public(pub)
            vc["issuer"] = did
            header = {"alg": "EdDSA", "typ": "JWT"}
            payload = {
                "iss": did,
                "nbf": int(datetime.now(timezone.utc).timestamp()),
                "vc": vc,
            }
            # Compact JWS: base64url(header) + '.' + base64url(payload) + '.' + base64url(signature)
            header_b64 = _b64url(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
            payload_b64 = _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
            signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
            signature = signer.sign(signing_input).signature  # 64 bytes
            signature_b64 = _b64url(signature)
            jws = f"{header_b64}.{payload_b64}.{signature_b64}"
            proof = {
                "type": "Ed25519Signature2020",
                "created": _now_iso(),
                "verificationMethod": did,
                "proofPurpose": "assertionMethod",
                "jws": jws,
            }
            return {"vc": vc, "proof": proof}
        except Exception:
            pass

    # Fallback: unsigned envelope
    header = {"alg": "none", "typ": "JWT"}
    payload = {"nbf": int(datetime.now(timezone.utc).timestamp()), "vc": vc}
    proof = {
        "type": "DataIntegrityProof",
        "created": _now_iso(),
        "verificationMethod": vc["issuer"],
        "proofPurpose": "assertionMethod",
        "jws": f"{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(payload).encode())}.",
        "note": "unsigned-dev-proof",
    }
    return {"vc": vc, "proof": proof}
