from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Tuple
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import requests

from . import iso
from .schemas import VerificationResult

try:
    from nacl import signing
    from nacl.exceptions import BadSignatureError
    from nacl.signing import VerifyKey
except Exception:  # pragma: no cover
    signing = None  # type: ignore

    class BadSignatureError(Exception):
        pass

    class _DummyVerifyKey:
        def verify(self, *args, **kwargs):
            raise BadSignatureError("nacl unavailable")

    VerifyKey = _DummyVerifyKey  # type: ignore


ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "artifacts"))
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

KEYS_DIR = Path(".keys")
DEV_SK_HEX = KEYS_DIR / "service_sk.hex"
DEV_PK_PEM = KEYS_DIR / "service_pk.pem"

ENV_SK_PATH = os.getenv("SERVICE_PRIVATE_KEY")
ENV_PK_PATH = os.getenv("SERVICE_PUBLIC_KEY")


def _sha256_hex(data: bytes) -> str:
    return "0x" + hashlib.sha256(data).hexdigest()


def _serialize_json(obj: Any) -> Any:
    if isinstance(obj, datetime):
        if obj.tzinfo:
            return obj.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return obj.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(obj, Decimal):
        return format(obj, "f")
    return obj


def _to_pem(pk_raw: bytes) -> str:
    import base64

    b64 = base64.b64encode(pk_raw).decode("ascii")
    wrapped = "\n".join(b64[i : i + 64] for i in range(0, len(b64), 64))
    return "-----BEGIN ED25519 PUBLIC KEY-----\n" + wrapped + "\n-----END ED25519 PUBLIC KEY-----\n"


def _pem_to_raw(pem_text: str) -> bytes:
    import base64

    lines = [ln.strip() for ln in pem_text.strip().splitlines() if "-----" not in ln]
    b64 = "".join(lines)
    return base64.b64decode(b64)


def _ensure_keys() -> Tuple[Any, bytes, str]:
    """Return (signing_key, raw_public_key_bytes, pem_text).

    Preference:
      1) SERVICE_PRIVATE_KEY (hex seed) + SERVICE_PUBLIC_KEY (PEM) file paths via env
      2) Dev fallback: generate keypair into .keys/
    """

    if signing is None:  # type: ignore
        # Provide deterministic placeholders; signature verification will be skipped.
        class _DummySK:
            def sign(self, data: bytes):
                class _Sig:
                    signature = b""

                return _Sig()

        pem_text = "-----BEGIN ED25519 PUBLIC KEY-----\nUNAVAILABLE\n-----END ED25519 PUBLIC KEY-----\n"
        return _DummySK(), b"", pem_text

    # 1) Use provided keys
    if ENV_SK_PATH and Path(ENV_SK_PATH).exists():
        seed_hex = Path(ENV_SK_PATH).read_text().strip().lower().replace("0x", "")
        seed = bytes.fromhex(seed_hex)
        if len(seed) not in (32, 64):
            raise ValueError("SERVICE_PRIVATE_KEY must contain 32-byte hex seed or 64-byte expanded key")
        if len(seed) == 64:
            seed = seed[:32]
        sk = signing.SigningKey(seed)
        pk_raw = sk.verify_key.encode()
        if ENV_PK_PATH and Path(ENV_PK_PATH).exists():
            pem_text = Path(ENV_PK_PATH).read_text(encoding="utf-8")
        else:
            pem_text = _to_pem(pk_raw)
        return sk, pk_raw, pem_text

    # 2) Dev fallback: generate and persist locally
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if DEV_SK_HEX.exists() and DEV_PK_PEM.exists():
        seed_hex = DEV_SK_HEX.read_text().strip()
        sk = signing.SigningKey(bytes.fromhex(seed_hex))
        pk_raw = sk.verify_key.encode()
        pem_text = DEV_PK_PEM.read_text(encoding="utf-8")
        return sk, pk_raw, pem_text

    sk = signing.SigningKey.generate()
    pk_raw = sk.verify_key.encode()
    pem_text = _to_pem(pk_raw)
    DEV_SK_HEX.write_text(sk.encode().hex())
    DEV_PK_PEM.write_text(pem_text)
    return sk, pk_raw, pem_text


def _canonical_manifest_bytes(manifest: Dict[str, Any]) -> bytes:
    """Canonical JSON bytes used for signing.

    We use compact encoding with sorted keys to ensure stable signatures.
    """
    return json.dumps(manifest, separators=(",", ":"), sort_keys=True, default=_serialize_json).encode("utf-8")


def _deterministic_zip(file_map: Dict[str, bytes], out_path: Path) -> bytes:
    """Create a deterministic ZIP.

    - sorted filenames
    - fixed timestamps (1980-01-01 00:00:00)
    - fixed permissions
    - ZIP_STORED (no compression)
    """

    out_path.parent.mkdir(parents=True, exist_ok=True)

    mem = io.BytesIO()
    with ZipFile(mem, mode="w", compression=ZIP_STORED) as zf:
        for name in sorted(file_map.keys()):
            zi = ZipInfo(filename=name, date_time=(1980, 1, 1, 0, 0, 0))
            zi.external_attr = 0o644 << 16
            zf.writestr(zi, file_map[name])

    data = mem.getvalue()
    out_path.write_bytes(data)
    return data


def create_bundle(receipt: Dict[str, Any], xml_bytes: bytes) -> Tuple[str, str]:
    """Build a deterministic evidence bundle and return (zip_path, bundle_hash).

    Bundle is self-contained:
      - pain001.xml
      - receipt.json
      - tip.json
      - manifest.json (canonical)
      - manifest.sig (Ed25519 signature over canonical manifest.json)
      - public_key.pem
      - optional: credential.json, ivms101.json

    Anchoring should anchor the **hash of the entire evidence.zip**.
    """

    rid = str(receipt["id"])
    out_dir = ARTIFACTS_DIR / rid
    out_dir.mkdir(parents=True, exist_ok=True)

    pain_xml = xml_bytes

    receipt_json = json.dumps(
        {
            "id": rid,
            "reference": receipt.get("reference"),
            "tip_tx_hash": receipt.get("tip_tx_hash"),
            "chain": receipt.get("chain"),
            "amount": _serialize_json(receipt.get("amount")),
            "currency": receipt.get("currency"),
            "sender_wallet": receipt.get("sender_wallet"),
            "receiver_wallet": receipt.get("receiver_wallet"),
            "status": receipt.get("status"),
            "created_at": _serialize_json(receipt.get("created_at")),
        },
        indent=2,
        separators=(",", ": "),
        default=_serialize_json,
    ).encode("utf-8")

    tip_json = json.dumps(
        {
            "reference": receipt.get("reference"),
            "tip_tx_hash": receipt.get("tip_tx_hash"),
            "chain": receipt.get("chain"),
            "amount": _serialize_json(receipt.get("amount")),
            "currency": receipt.get("currency"),
            "sender_wallet": receipt.get("sender_wallet"),
            "receiver_wallet": receipt.get("receiver_wallet"),
        },
        indent=2,
        separators=(",", ": "),
        default=_serialize_json,
    ).encode("utf-8")

    # Optional extra files passed via receipt dict
    extra_files: Dict[str, bytes] = {}
    try:
        vc_cred = receipt.get("vc_credential")
        if vc_cred is not None:
            extra_files["credential.json"] = json.dumps(
                vc_cred, indent=2, separators=(",", ": "), default=_serialize_json
            ).encode("utf-8")
    except Exception:
        pass

    try:
        ivms = receipt.get("ivms101")
        if ivms is not None:
            extra_files["ivms101.json"] = json.dumps(
                ivms, indent=2, separators=(",", ": "), default=_serialize_json
            ).encode("utf-8")
    except Exception:
        pass

    files_for_manifest = {
        "pain001.xml": pain_xml,
        "receipt.json": receipt_json,
        "tip.json": tip_json,
        **extra_files,
    }

    manifest: Dict[str, Any] = {
        "version": "1.0",
        "reference": receipt.get("reference"),
        "receipt_id": rid,
        "created_at": _serialize_json(receipt.get("created_at")),
        "files": [
            {
                "name": name,
                "sha256": _sha256_hex(content),
                "size": len(content),
            }
            for name, content in sorted(files_for_manifest.items())
        ],
    }

    # Canonical manifest bytes used for signature
    manifest_canon = _canonical_manifest_bytes(manifest)

    # Signing keys
    sk, _pk_raw, pk_pem = _ensure_keys()

    # Sign canonical manifest bytes (not the zip hash)
    manifest_sig = b""
    if signing is not None:  # type: ignore
        manifest_sig = sk.sign(manifest_canon).signature

    # Public-key pem is included in zip for portable verification
    file_map: Dict[str, bytes] = {
        "pain001.xml": pain_xml,
        "receipt.json": receipt_json,
        "tip.json": tip_json,
        "manifest.json": manifest_canon,
        "manifest.sig": manifest_sig,
        "public_key.pem": pk_pem.encode("utf-8"),
        **extra_files,
    }

    zip_path = out_dir / "evidence.zip"
    zip_bytes = _deterministic_zip(file_map, zip_path)

    bundle_hash = _sha256_hex(zip_bytes)

    # Persist convenience files
    (out_dir / "pain001.xml").write_bytes(pain_xml)
    (out_dir / "manifest.json").write_bytes(manifest_canon)
    (out_dir / "manifest.sig").write_text(manifest_sig.hex())
    (out_dir / "public_key.pem").write_text(pk_pem, encoding="utf-8")

    return str(zip_path), bundle_hash


def verify_bundle(bundle_url: str) -> VerificationResult:
    """Download a bundle, compute its hash, validate manifest, validate XML, verify manifest signature.

    Returns VerificationResult(bundle_hash, errors).
    """

    errors: List[str] = []

    # Download file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        try:
            resp = requests.get(bundle_url, stream=True, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            return VerificationResult(bundle_hash="", errors=[f"download_failed: {e}"])

        hasher = hashlib.sha256()
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                tmp.write(chunk)
                hasher.update(chunk)
        tmp.flush()
        bundle_path = Path(tmp.name)

    bundle_hash = "0x" + hasher.hexdigest()

    # Open zip and read contents
    try:
        with ZipFile(bundle_path, "r") as zf:

            def read(name: str) -> bytes:
                try:
                    with zf.open(name) as f:
                        return f.read()
                except KeyError:
                    errors.append(f"missing_file:{name}")
                    return b""

            manifest_bytes = read("manifest.json")
            sig_bytes = read("manifest.sig")
            xml_bytes = read("pain001.xml")
            pk_pem_bytes = read("public_key.pem")

            # Manifest validation
            try:
                manifest = json.loads(manifest_bytes.decode("utf-8"))
                # Verify canonical encoding matches what was signed
                canon = _canonical_manifest_bytes(manifest)
                if canon != manifest_bytes:
                    # Not fatal but indicates non-canonical formatting (should not happen for our bundles)
                    errors.append("manifest_not_canonical")
                for entry in manifest.get("files", []):
                    name = entry.get("name")
                    expected_sha = entry.get("sha256")
                    if not name or not expected_sha:
                        errors.append("manifest_entry_invalid")
                        continue
                    content = read(name)
                    actual = _sha256_hex(content)
                    if actual != expected_sha:
                        errors.append(f"file_hash_mismatch:{name}")
            except Exception as e:
                errors.append(f"manifest_invalid:{e}")

            # XML validation (if schema present)
            try:
                schema = iso._get_schema()  # type: ignore
                if schema is not None and xml_bytes:
                    schema.validate(xml_bytes)
            except Exception as e:
                errors.append(f"xml_invalid:{e}")

            # Signature verification (over canonical manifest)
            if signing is None:
                errors.append("signature_check_unavailable")
            else:
                try:
                    pk_raw = _pem_to_raw(pk_pem_bytes.decode("utf-8"))
                    vk = VerifyKey(pk_raw)
                    vk.verify(manifest_bytes, sig_bytes)
                except BadSignatureError:
                    errors.append("signature_invalid")
                except Exception as e:
                    errors.append(f"signature_check_failed:{e}")

    except Exception as e:
        errors.append(f"zip_open_failed:{e}")

    return VerificationResult(bundle_hash=bundle_hash, errors=errors)
