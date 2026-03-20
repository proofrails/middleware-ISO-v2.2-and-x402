from __future__ import annotations

"""On-chain anchoring and lookup (Python web3 path).

Key improvement vs earlier version:
- No reliance on module-level env state for RPC/contract/key.
- No os.environ mutation required by callers.

All functions accept explicit parameters, but still default to env vars for convenience.
"""

import json
import logging
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

logger = logging.getLogger(__name__)

# Default to Flare mainnet if not configured.
DEFAULT_RPC_URL = os.getenv("FLARE_RPC_URL", "https://flare-api.flare.network/ext/C/rpc")
FALLBACK_RPC_URL = os.getenv("FLARE_RPC_URL_FALLBACK", "")
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


def _short_hex(s: Optional[str], *, keep: int = 10) -> str:
    if not s or not isinstance(s, str):
        return ""
    if len(s) <= keep * 2:
        return s
    return f"{s[:keep]}…{s[-keep:]}"


def _hex32_from_prefixed(hex_str: str) -> bytes:
    if not isinstance(hex_str, str) or not hex_str.startswith("0x"):
        raise ValueError("bundle_hash must be 0x-prefixed hex string")
    hex_body = hex_str[2:]
    if len(hex_body) != 64:
        raise ValueError("bundle_hash must be 32-byte (64 hex chars)")
    return int(hex_body, 16).to_bytes(32, "big")


def _load_abi(abi_path: Optional[str]) -> List[Dict[str, Any]]:
    p = abi_path or DEFAULT_ABI_PATH
    try:
        if p and Path(p).exists():
            txt = Path(p).read_text(encoding="utf-8")
            abi = json.loads(txt)
            logger.debug("anchor_abi_loaded path=%s entries=%s", p, len(abi) if isinstance(abi, list) else "n/a")
            return abi
        logger.debug("anchor_abi_fallback path=%s", p)
        return FALLBACK_ABI
    except Exception:
        logger.exception("anchor_abi_load_failed path=%s", p)
        return FALLBACK_ABI


def _load_web3(rpc_url: Optional[str]) -> Web3:
    primary = rpc_url or DEFAULT_RPC_URL
    fallback = FALLBACK_RPC_URL

    # Try primary with a short timeout (2s) — if the public RPC is slow, fall back
    try:
        w3 = Web3(Web3.HTTPProvider(primary, request_kwargs={"timeout": 2}))
        if w3.is_connected():
            logger.debug("anchor_web3_loaded url=%s (primary)", primary)
            return Web3(Web3.HTTPProvider(primary, request_kwargs={"timeout": 30}))
    except Exception:
        pass

    # Primary slow or down — use fallback (local node)
    if fallback:
        try:
            w3 = Web3(Web3.HTTPProvider(fallback, request_kwargs={"timeout": 30}))
            if w3.is_connected():
                logger.info("anchor_web3_fallback url=%s (primary %s was slow/down)", fallback, primary)
                return w3
        except Exception:
            pass

    # Both failed — return primary with normal timeout, let caller handle errors
    logger.error("anchor_web3_all_rpcs_failed, returning primary url=%s", primary)
    return Web3(Web3.HTTPProvider(primary, request_kwargs={"timeout": 30}))


def _load_contract(
    *, rpc_url: Optional[str], contract_addr: Optional[str], abi_path: Optional[str]
) -> Tuple[Web3, Contract]:
    w3 = _load_web3(rpc_url)
    addr = contract_addr or DEFAULT_CONTRACT_ADDR
    if not addr:
        logger.error("anchor_contract_addr_missing")
        raise RuntimeError("ANCHOR_CONTRACT_ADDR is not set")

    abi = _load_abi(abi_path)
    try:
        caddr = to_checksum_address(addr)
    except Exception:
        logger.exception("anchor_contract_addr_invalid addr=%s", addr)
        raise

    try:
        contract = w3.eth.contract(address=caddr, abi=abi)
        logger.debug("anchor_contract_loaded addr=%s", caddr)
        return w3, contract
    except Exception:
        logger.exception("anchor_contract_load_failed addr=%s", addr)
        raise


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
            logger.debug("anchor_fee_history_reward_parse_failed", exc_info=True)

        max_priority = tip
        max_fee = base * 2 + max_priority
        logger.debug("anchor_fees_eip1559 base=%s max_fee=%s max_prio=%s", base, max_fee, max_priority)
        return max_fee, max_priority
    except Exception:
        logger.debug("anchor_fees_eip1559_unavailable", exc_info=True)
        return None


def _build_tx_anchor(w3: Web3, contract: Contract, from_addr: str, bundle_hash32: bytes) -> Dict[str, Any]:
    func = contract.functions.anchorEvidence(bundle_hash32)
    try:
        nonce = w3.eth.get_transaction_count(from_addr, "pending")
    except Exception:
        logger.exception("anchor_get_nonce_failed from=%s", from_addr)
        raise

    try:
        chain_id = w3.eth.chain_id
    except Exception:
        logger.exception("anchor_get_chain_id_failed")
        raise

    tx: Dict[str, Any] = {
        "from": from_addr,
        "nonce": nonce,
        "chainId": chain_id,
    }

    fees = _estimate_fees_eip1559(w3)
    if fees:
        max_fee, max_priority = fees
        tx.update({"type": 2, "maxFeePerGas": max_fee, "maxPriorityFeePerGas": max_priority})
    else:
        try:
            gp = w3.eth.gas_price
            tx.update({"gasPrice": gp})
            logger.debug("anchor_gas_price_legacy gasPrice=%s", int(gp))
        except Exception:
            logger.exception("anchor_gas_price_failed")
            raise

    try:
        gas_est = func.estimate_gas({"from": from_addr})
        gas_est = int(int(gas_est) * 1.2)
        logger.debug("anchor_gas_estimated gas=%s", gas_est)
    except Exception:
        gas_est = 200_000
        logger.warning("anchor_gas_estimate_failed using_default=%s", gas_est, exc_info=True)

    tx.update({"gas": gas_est})

    try:
        built = func.build_transaction(tx)
        logger.debug(
            "anchor_tx_built from=%s nonce=%s chainId=%s gas=%s type=%s",
            from_addr,
            nonce,
            chain_id,
            built.get("gas"),
            built.get("type", "legacy"),
        )
        return built
    except Exception:
        logger.exception("anchor_tx_build_failed from=%s nonce=%s", from_addr, nonce)
        raise


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
        logger.error("anchor_private_key_missing")
        raise RuntimeError("ANCHOR_PRIVATE_KEY is not set")

    logger.info(
        "anchor_bundle_start bundle=%s rpc_url=%s contract=%s",
        _short_hex(bundle_hash_hex),
        rpc_url or DEFAULT_RPC_URL,
        contract_addr or DEFAULT_CONTRACT_ADDR,
    )

    w3, contract = _load_contract(rpc_url=rpc_url, contract_addr=contract_addr, abi_path=abi_path)

    try:
        acct = w3.eth.account.from_key(pk)
    except Exception:
        logger.exception("anchor_account_from_key_failed")
        raise

    try:
        bundle_hash32 = _hex32_from_prefixed(bundle_hash_hex)
    except Exception:
        logger.exception("anchor_bundle_hash_invalid bundle=%s", bundle_hash_hex)
        raise

    last_err: Optional[Exception] = None
    for attempt in range(3):
        try:
            logger.info("anchor_send_try attempt=%s from=%s", attempt + 1, acct.address)
            tx = _build_tx_anchor(w3, contract, acct.address, bundle_hash32)

            try:
                signed = acct.sign_transaction(tx)
            except Exception:
                logger.exception("anchor_sign_failed attempt=%s from=%s", attempt + 1, acct.address)
                raise

            try:
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            except Exception:
                logger.exception("anchor_send_raw_failed attempt=%s from=%s", attempt + 1, acct.address)
                raise

            txid = tx_hash.hex()
            logger.info("anchor_tx_sent attempt=%s txid=%s", attempt + 1, txid)

            try:
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            except Exception:
                logger.exception("anchor_wait_receipt_failed attempt=%s txid=%s", attempt + 1, txid)
                raise

            status = int(receipt.get("status", 1) or 0) if receipt else 0
            blk_no = int(receipt.get("blockNumber") or 0) if receipt else 0

            if receipt and status == 1:
                logger.info("anchor_success txid=%s block=%s", txid, blk_no)
                return txid, blk_no

            last_err = RuntimeError(f"Transaction failed with status={status}")
            logger.error("anchor_failed_status txid=%s block=%s status=%s", txid, blk_no, status)
        except Exception as e:
            last_err = e
            logger.warning("anchor_attempt_failed attempt=%s err=%s", attempt + 1, repr(e), exc_info=True)
            time.sleep(1 + attempt)

    logger.error("anchor_bundle_failed_final bundle=%s err=%s", _short_hex(bundle_hash_hex), repr(last_err))
    raise last_err or RuntimeError("Unknown error anchoring bundle")


def anchor_send(
    bundle_hash_hex: str,
    *,
    nonce: int,
    rpc_url: Optional[str] = None,
    contract_addr: Optional[str] = None,
    private_key: Optional[str] = None,
    abi_path: Optional[str] = None,
) -> Tuple[str, int]:
    """Send an anchor transaction without waiting for confirmation.

    Returns: (tx_hash_hex, nonce_used)
    """
    pk = private_key or os.getenv("ANCHOR_PRIVATE_KEY")
    if not pk:
        raise RuntimeError("ANCHOR_PRIVATE_KEY is not set")

    w3, contract = _load_contract(rpc_url=rpc_url, contract_addr=contract_addr, abi_path=abi_path)
    acct = w3.eth.account.from_key(pk)
    bundle_hash32 = _hex32_from_prefixed(bundle_hash_hex)

    # Build transaction with the provided nonce (bypass _build_tx_anchor's nonce fetch)
    func = contract.functions.anchorEvidence(bundle_hash32)

    try:
        chain_id = w3.eth.chain_id
    except Exception:
        logger.exception("anchor_send_get_chain_id_failed")
        raise

    tx: Dict[str, Any] = {
        "from": acct.address,
        "nonce": nonce,
        "chainId": chain_id,
    }

    fees = _estimate_fees_eip1559(w3)
    if fees:
        max_fee, max_priority = fees
        tx.update({"type": 2, "maxFeePerGas": max_fee, "maxPriorityFeePerGas": max_priority})
    else:
        gp = w3.eth.gas_price
        tx.update({"gasPrice": gp})

    try:
        gas_est = func.estimate_gas({"from": acct.address})
        gas_est = int(int(gas_est) * 1.2)
    except Exception:
        gas_est = 200_000

    tx["gas"] = gas_est
    built = func.build_transaction(tx)

    signed = acct.sign_transaction(built)

    # send_raw_transaction can hang indefinitely on unresponsive nodes.
    # Use a thread with a hard timeout to avoid blocking the worker.
    import concurrent.futures
    send_timeout = int(os.getenv("ANCHOR_SEND_TIMEOUT", "30"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(w3.eth.send_raw_transaction, signed.raw_transaction)
        try:
            tx_hash = future.result(timeout=send_timeout)
        except concurrent.futures.TimeoutError:
            raise RuntimeError(f"send_raw_transaction timed out after {send_timeout}s")
    txid = tx_hash.hex()

    logger.info("anchor_send_ok txid=%s nonce=%s bundle=%s", txid, nonce, _short_hex(bundle_hash_hex))
    return txid, nonce


def anchor_confirm(
    tx_hash_hex: str,
    *,
    rpc_url: Optional[str] = None,
) -> Optional[Tuple[bool, int, int]]:
    """Check if a transaction has been confirmed.

    Returns: (success, status_int, block_number) or None if still pending.
    """
    w3 = _load_web3(rpc_url)
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash_hex)
    except Exception:
        # Transaction not yet mined or RPC error
        return None

    if receipt is None:
        return None

    status = int(receipt.get("status", 0) or 0)
    blk_no = int(receipt.get("blockNumber") or 0)
    return (status == 1, status, blk_no)


def find_anchor(
    bundle_hash_hex: str,
    *,
    rpc_url: Optional[str] = None,
    contract_addr: Optional[str] = None,
    abi_path: Optional[str] = None,
    lookback_blocks: Optional[int] = None,
) -> ChainMatch:
    """Find EvidenceAnchored event for a given bundle hash."""
    logger.debug(
        "find_anchor_start bundle=%s rpc_url=%s contract=%s lookback=%s",
        _short_hex(bundle_hash_hex),
        rpc_url or DEFAULT_RPC_URL,
        contract_addr or DEFAULT_CONTRACT_ADDR,
        lookback_blocks if lookback_blocks is not None else DEFAULT_LOOKBACK_BLOCKS,
    )

    try:
        w3, contract = _load_contract(rpc_url=rpc_url, contract_addr=contract_addr, abi_path=abi_path)
    except Exception:
        logger.warning("find_anchor_contract_load_failed bundle=%s", _short_hex(bundle_hash_hex), exc_info=True)
        return ChainMatch(matches=False)

    try:
        bundle_hash32 = _hex32_from_prefixed(bundle_hash_hex)
    except Exception:
        logger.warning("find_anchor_invalid_bundle_hash bundle=%s", bundle_hash_hex, exc_info=True)
        return ChainMatch(matches=False)

    lb = int(lookback_blocks if lookback_blocks is not None else DEFAULT_LOOKBACK_BLOCKS)

    try:
        latest = w3.eth.block_number
    except Exception:
        logger.warning("find_anchor_block_number_failed", exc_info=True)
        return ChainMatch(matches=False)

    from_block = max(0, latest - lb)

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
        logger.debug("find_anchor_logs_fetched method=get_logs count=%s", len(logs))
    except Exception:
        logger.debug("find_anchor_get_logs_failed trying_filter", exc_info=True)
        try:
            evt_filter = contract.events.EvidenceAnchored().create_filter(fromBlock=from_block, toBlock=latest)  # type: ignore
            logs = evt_filter.get_all_entries()  # type: ignore
            logger.debug("find_anchor_logs_fetched method=filter count=%s", len(logs))
        except Exception:
            logger.warning("find_anchor_logs_failed bundle=%s", _short_hex(bundle_hash_hex), exc_info=True)
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
                blk_no = int(log["blockNumber"])
                anchored_at: Optional[datetime] = None
                try:
                    blk = w3.eth.get_block(blk_no)
                    ts = blk.get("timestamp")
                    anchored_at = datetime.fromtimestamp(ts, tz=timezone.utc) if isinstance(ts, int) else None
                except Exception:
                    logger.debug("find_anchor_get_block_failed block=%s", blk_no, exc_info=True)

                logger.info("find_anchor_match bundle=%s txid=%s block=%s", _short_hex(bundle_hash_hex), tx_hash, blk_no)
                return ChainMatch(matches=True, txid=tx_hash, anchored_at=anchored_at)
        except Exception:
            logger.debug("find_anchor_log_decode_failed", exc_info=True)
            continue

    logger.info("find_anchor_no_match bundle=%s from_block=%s to_block=%s", _short_hex(bundle_hash_hex), from_block, latest)
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
    logger.debug(
        "verify_anchor_tx_start txid=%s expected_bundle=%s rpc_url=%s contract=%s",
        _short_hex(txid),
        _short_hex(expected_bundle_hash_hex),
        rpc_url or DEFAULT_RPC_URL,
        contract_addr or DEFAULT_CONTRACT_ADDR,
    )

    if not txid or not isinstance(txid, str) or not txid.startswith("0x"):
        logger.warning("verify_anchor_tx_invalid_txid txid=%r", txid)
        return False, None, None

    try:
        expected = _hex32_from_prefixed(expected_bundle_hash_hex)
    except Exception:
        logger.warning("verify_anchor_tx_invalid_expected_bundle expected=%r", expected_bundle_hash_hex, exc_info=True)
        return False, None, None

    try:
        w3 = _load_web3(rpc_url)
        receipt = w3.eth.get_transaction_receipt(txid)
        if not receipt:
            logger.info("verify_anchor_tx_no_receipt txid=%s", txid)
            return False, None, None

        status = int(receipt.get("status", 1) or 0)
        blk_no = int(receipt.get("blockNumber") or 0)
        if status != 1:
            logger.info("verify_anchor_tx_failed_status txid=%s block=%s status=%s", txid, blk_no, status)
            return False, blk_no, None

        caddr = contract_addr or DEFAULT_CONTRACT_ADDR
        if not caddr:
            logger.warning("verify_anchor_tx_contract_addr_missing txid=%s", txid)
            return False, blk_no, None
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

                if len(data_bytes) < 64:
                    continue

                bundle_hash32 = data_bytes[:32]
                if bundle_hash32 != expected:
                    continue

                anchored_at: Optional[datetime] = None
                try:
                    blk = w3.eth.get_block(blk_no)
                    ts = blk.get("timestamp")
                    if isinstance(ts, int):
                        anchored_at = datetime.fromtimestamp(ts, tz=timezone.utc)
                except Exception:
                    logger.debug("verify_anchor_tx_get_block_failed block=%s", blk_no, exc_info=True)
                    anchored_at = None

                logger.info("verify_anchor_tx_match txid=%s block=%s", txid, blk_no)
                return True, blk_no, anchored_at
            except Exception:
                logger.debug("verify_anchor_tx_log_parse_failed txid=%s", txid, exc_info=True)
                continue

        logger.info("verify_anchor_tx_no_match txid=%s block=%s", txid, blk_no)
        return False, blk_no, None
    except Exception:
        logger.warning("verify_anchor_tx_exception txid=%s", txid, exc_info=True)
        return False, None, None
