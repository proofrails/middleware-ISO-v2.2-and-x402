#!/usr/bin/env python3
"""Independently verify a public ProofRails receipt, bundle and Flare anchor."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import urllib.request
import zipfile

from cryptography.hazmat.primitives import serialization

API = "https://app.proofrails.com"
RPC = "https://flare-api.flare.network/ext/C/rpc"
EVIDENCE_ANCHOR = "0x235f83a74fc9d759d648ec533d2c06712f3ca5ea"
EVIDENCE_TOPIC0 = "0xd414fe2d5071ea63896cf41c2e5a7bdd46aed543a8c8e83357a1ae468a383419"
DEFAULT_RECEIPT = "dec5a106-3216-4543-bfb6-e669dc83f4d7"


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def get_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def rpc(method: str, params: list) -> object:
    request = urllib.request.Request(
        RPC,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload["result"]


def prefixed_sha256(data: bytes) -> str:
    return "0x" + hashlib.sha256(data).hexdigest()


def main(receipt_id: str) -> None:
    receipt = get_json(f"{API}/v1/iso/receipts/{receipt_id}")
    if receipt["status"] != "anchored":
        raise RuntimeError(f"Receipt is not complete: {receipt['status']}")

    bundle = get_bytes(receipt["bundle_url"])
    bundle_hash = prefixed_sha256(bundle)
    if bundle_hash.lower() != receipt["bundle_hash"].lower():
        raise RuntimeError("Downloaded ZIP hash does not match the receipt")

    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RuntimeError(f"ZIP CRC failed: {bad_member}")
        manifest_bytes = archive.read("manifest.json")
        manifest = json.loads(manifest_bytes)
        for entry in manifest["files"]:
            payload = archive.read(entry["name"])
            if len(payload) != entry["size"]:
                raise RuntimeError(f"Size mismatch: {entry['name']}")
            if prefixed_sha256(payload).lower() != entry["sha256"].lower():
                raise RuntimeError(f"Hash mismatch: {entry['name']}")
        public_key = serialization.load_pem_public_key(archive.read("public_key.pem"))
        public_key.verify(archive.read("manifest.sig"), manifest_bytes)

    if rpc("eth_chainId", []) != "0xe":
        raise RuntimeError("RPC is not Flare mainnet chain ID 14")
    tx_hash = receipt["flare_txid"]
    if not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash
    chain_receipt = rpc("eth_getTransactionReceipt", [tx_hash])
    if not chain_receipt or chain_receipt["status"] != "0x1":
        raise RuntimeError("Anchor transaction is missing or failed")

    matches = [
        log for log in chain_receipt["logs"]
        if log["address"].lower() == EVIDENCE_ANCHOR
        and log.get("topics", [None])[0].lower() == EVIDENCE_TOPIC0
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one EvidenceAnchored event, found {len(matches)}")
    event_bundle_hash = "0x" + matches[0]["data"][2:66]
    if event_bundle_hash.lower() != bundle_hash.lower():
        raise RuntimeError("EvidenceAnchored bundleHash does not match the current ZIP")

    print(json.dumps({
        "receipt_id": receipt_id,
        "status": receipt["status"],
        "bundle_hash": bundle_hash,
        "anchor_transaction": tx_hash,
        "evidence_anchor": EVIDENCE_ANCHOR,
        "manifest_entries": len(manifest["files"]),
        "zip_crc": "pass",
        "manifest_signature": "pass",
        "onchain_hash_match": True,
        "boundary": "Integrity and timing verified; offchain truth and legal sufficiency not established",
    }, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RECEIPT)
