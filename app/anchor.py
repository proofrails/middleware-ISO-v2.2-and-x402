from __future__ import annotations

"""On-chain anchoring and lookup (Python web3 path).

Key improvement vs earlier version:
- No reliance on module-level env state for RPC/contract/key.
- No os.environ mutation required by callers.

All functions accept explicit parameters, but still default to env vars for convenience.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from eth_utils import to_checksum_address  # type: ignore
from hexbytes import HexBytes  # type: ignore
from web3 import Web3  # type: ignore
from web3.contract import Contract  # type: ignore

from .schemas import ChainMatch

# Default to Flare mainnet if not configured.
DEFAULT_RPC_URL = os.getenv("FLARE_RPC_URL", "https://flare-api.flare.network/ext/C/rpc")
# If ANCHOR_CONTRACT_ADDR is not set, fall back to the platform-hosted mainnet contract.
DEFAULT_CONTRACT_ADDR = os.getenv("ANCHOR_CONTRACT_ADDR", "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8")
DEFAULT_ABI_PATH = os.getenv("ANCHOR_ABI_PATH", "contracts/EvidenceAnchor.abi.json")
DEFAULT_LOOKBACK_BLOCKS = int(os.getenv("ANCHOR_LOOKBACK_BLOCKS", "50000"))

# Minimal ABI fallback if file not provided.
# Matches: function anchorEvidence(bytes32 bundleHash)
#          event EvidenceAnchored(bytes32 bundleHash, address sender, uint256 ts)
FALLBACK_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "internalType": "bytes32", "name": "bundleHash", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "sender", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "ts", "type": "uint256"},
        ],
        "name": "EvidenceAnchored",
        "type": "event",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "bundleHash", "type": "bytes32"}],
        "name": "anchorEvidence",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


def _hex32_from_prefixed(hex_str: str) -> bytes:
    if not isinstance(hex_str, str) or not hex_str.startswith("0x"):
        raise ValueError("bundle_hash must be 0x-prefixed hex string")
    hex_body = hex_str[2:]
    if len(hex_body) != 64:
        raise ValueError("bundle_hash must be 32-byte (64 hex chars)")
    return int(hex_body, 16).to_bytes(32, "big")


def _load_abi(abi_path: Optional[str]) -> List[Dict[str, Any]]:
    p = abi_path or DEFAULT_ABI_PATH
    if p and Path(p).exists():
        return json.loads(Path(p).read_text(encoding="utf-8"))
    return FALLBACK_ABI


def _load_web3(rpc_url: Optional[str]) -> Web3:
    return Web3(Web3.HTTPProvider(rpc_url or DEFAULT_RPC_URL))


def _load_contract(
    *, rpc_url: Optional[str], contract_addr: Optional[str], abi_path: Optional[str]
) -> Tuple[Web3, Contract]:
    w3 = _load_web3(rpc_url)
    addr = contract_addr or DEFAULT_CONTRACT_ADDR
    if not addr:
        raise RuntimeError("ANCHOR_CONTRACT_ADDR is not set")
    abi = _load_abi(abi_path)
    contract = w3.eth.contract(address=to_checksum_address(addr), abi=abi)
    return w3, contract


def _estimate_fees_eip1559(w3: Web3) -> Optional[Tuple[int, int]]:
    try:
        history = w3.eth.fee_history(5, "latest", [10, 50, 90])
        base_fees = history["baseFeePerGas"]
        base = int(base_fees[-1])
        tip = int(2e9)
        try:
            prio = history.get("reward", [])
            if prio and prio[-1]:
                tip = max(tip, int(prio[-1][1]))
        except Exception:
            pass
        max_priority = tip
        max_fee = base * 2 + max_priority
        return max_fee, max_priority
    except Exception:
        return None


def _build_tx_anchor(w3: Web3, contract: Contract, from_addr: str, bundle_hash32: bytes) -> Dict[str, Any]:
    func = contract.functions.anchorEvidence(bundle_hash32)
    tx: Dict[str, Any] = {
        "from": from_addr,
        "nonce": w3.eth.get_transaction_count(from_addr, "pending"),
        "chainId": w3.eth.chain_id,
    }

    fees = _estimate_fees_eip1559(w3)
    if fees:
        max_fee, max_priority = fees
        tx.update({"type": 2, "maxFeePerGas": max_fee, "maxPriorityFeePerGas": max_priority})
    else:
        tx.update({"gasPrice": w3.eth.gas_price})

    try:
        gas_est = func.estimate_gas({"from": from_addr})
        gas_est = int(gas_est * 1.2)
    except Exception:
        gas_est = 200_000

    tx.update({"gas": gas_est})
    return func.build_transaction(tx)


def anchor_bundle(
    bundle_hash_hex: str,
    *,
    rpc_url: Optional[str] = None,
    contract_addr: Optional[str] = None,
    private_key: Optional[str] = None,
    abi_path: Optional[str] = None,
    lookback_blocks: Optional[int] = None,
) -> Tuple[str, int]:
    """Anchor the 32-byte bundle hash on-chain.

    Returns: (txid_hex, blockNumber)

    Notes:
    - `lookback_blocks` is accepted for interface symmetry (used by find_anchor).
    """

    _ = lookback_blocks

    pk = private_key or os.getenv("ANCHOR_PRIVATE_KEY")
    if not pk:
        raise RuntimeError("ANCHOR_PRIVATE_KEY is not set")

    w3, contract = _load_contract(rpc_url=rpc_url, contract_addr=contract_addr, abi_path=abi_path)
    acct = w3.eth.account.from_key(pk)

    bundle_hash32 = _hex32_from_prefixed(bundle_hash_hex)

    last_err: Optional[Exception] = None
    for attempt in range(3):
        try:
            tx = _build_tx_anchor(w3, contract, acct.address, bundle_hash32)
            signed = acct.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            if receipt and receipt.get("status", 1) == 1:
                return tx_hash.hex(), int(receipt["blockNumber"])
            last_err = RuntimeError("Transaction failed with status != 1")
        except Exception as e:
            last_err = e
            time.sleep(1 + attempt)

    raise last_err or RuntimeError("Unknown error anchoring bundle")


def find_anchor(
    bundle_hash_hex: str,
    *,
    rpc_url: Optional[str] = None,
    contract_addr: Optional[str] = None,
    abi_path: Optional[str] = None,
    lookback_blocks: Optional[int] = None,
) -> ChainMatch:
    """Find EvidenceAnchored event for a given bundle hash."""

    try:
        w3, contract = _load_contract(rpc_url=rpc_url, contract_addr=contract_addr, abi_path=abi_path)
    except Exception:
        return ChainMatch(matches=False)

    try:
        bundle_hash32 = _hex32_from_prefixed(bundle_hash_hex)
    except Exception:
        return ChainMatch(matches=False)

    lb = int(lookback_blocks if lookback_blocks is not None else DEFAULT_LOOKBACK_BLOCKS)

    latest = w3.eth.block_number
    from_block = max(0, latest - lb)

    # Filter by event signature only; bundleHash may not be indexed.
    try:
        event = contract.events.EvidenceAnchored()  # type: ignore
        topic0 = event._get_event_topic()  # type: ignore
        logs = w3.eth.get_logs(
            {
                "fromBlock": from_block,
                "toBlock": latest,
                "address": contract.address,
                "topics": [topic0],
            }
        )
    except Exception:
        try:
            evt_filter = contract.events.EvidenceAnchored().create_filter(fromBlock=from_block, toBlock=latest)  # type: ignore
            logs = evt_filter.get_all_entries()  # type: ignore
        except Exception:
            logs = []

    for log in reversed(logs):
        try:
            decoded = contract.events.EvidenceAnchored().process_log(log)  # type: ignore
            args = decoded["args"]
            ev_hash: bytes = args.get("bundleHash", b"")
            if isinstance(ev_hash, HexBytes):
                ev_hash = bytes(ev_hash)
            if ev_hash == bundle_hash32:
                tx_hash = log["transactionHash"].hex()
                blk = w3.eth.get_block(log["blockNumber"])
                ts = blk.get("timestamp")
                anchored_at = datetime.fromtimestamp(ts, tz=timezone.utc) if isinstance(ts, int) else None
                return ChainMatch(matches=True, txid=tx_hash, anchored_at=anchored_at)
        except Exception:
            continue

    return ChainMatch(matches=False)


# --- Transaction-level verification helpers (used by tenant confirm-anchor) ---

# topic0 = keccak256("EvidenceAnchored(bytes32,address,uint256)")
EVIDENCE_ANCHORED_TOPIC0 = Web3.keccak(text="EvidenceAnchored(bytes32,address,uint256)")


def verify_anchor_tx(
    *,
    txid: str,
    expected_bundle_hash_hex: str,
    rpc_url: Optional[str] = None,
    contract_addr: Optional[str] = None,
) -> Tuple[bool, Optional[int], Optional[datetime]]:
    """Verify that a given transaction anchored the expected bundle hash.

    Intended for tenant/self-hosted mode: tenant submits a tx, platform validates.

    Returns: (matches, block_number, anchored_at)
    """

    if not txid or not isinstance(txid, str) or not txid.startswith("0x"):
        return False, None, None

    try:
        expected = _hex32_from_prefixed(expected_bundle_hash_hex)
    except Exception:
        return False, None, None

    try:
        w3 = _load_web3(rpc_url)
        receipt = w3.eth.get_transaction_receipt(txid)
        if not receipt:
            return False, None, None
        if int(receipt.get("status", 1) or 0) != 1:
            return False, int(receipt.get("blockNumber") or 0), None

        caddr = contract_addr or DEFAULT_CONTRACT_ADDR
        if not caddr:
            return False, int(receipt.get("blockNumber") or 0), None
        caddr = to_checksum_address(caddr)

        logs = receipt.get("logs") or []
        for lg in logs:
            try:
                addr = lg.get("address")
                if not addr:
                    continue
                if to_checksum_address(addr) != caddr:
                    continue

                topics = lg.get("topics") or []
                if not topics:
                    continue

                t0 = topics[0]
                t0_bytes = bytes(t0) if not isinstance(t0, (bytes, bytearray)) else bytes(t0)
                if t0_bytes != bytes(EVIDENCE_ANCHORED_TOPIC0):
                    continue

                data = lg.get("data")
                if isinstance(data, HexBytes):
                    data_bytes = bytes(data)
                elif isinstance(data, (bytes, bytearray)):
                    data_bytes = bytes(data)
                elif isinstance(data, str):
                    data_bytes = bytes(HexBytes(data))
                else:
                    continue

                # Non-indexed args are ABI-encoded in data:
                # - bundleHash (bytes32) at offset 0
                # - ts (uint256) at offset 32
                if len(data_bytes) < 64:
                    continue

                bundle_hash32 = data_bytes[:32]
                if bundle_hash32 != expected:
                    continue

                blk_no = int(receipt.get("blockNumber") or 0)
                anchored_at: Optional[datetime] = None
                try:
                    blk = w3.eth.get_block(blk_no)
                    ts = blk.get("timestamp")
                    if isinstance(ts, int):
                        anchored_at = datetime.fromtimestamp(ts, tz=timezone.utc)
                except Exception:
                    anchored_at = None

                return True, blk_no, anchored_at
            except Exception:
                continue

        return False, int(receipt.get("blockNumber") or 0), None
    except Exception:
        return False, None, None
