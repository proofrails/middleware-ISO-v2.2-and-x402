"""Flare FTSO v2 on-chain price feed reader.

Fetches tamper-proof exchange rates directly from Flare's on-chain FTSO v2
oracle system. Rates are updated every ~90 seconds by independent data
providers and stored on Flare's C-Chain.

How it works
------------
1. ``FlareContractRegistry`` at a known stable address exposes a
   ``getContractAddressByName`` method that returns live contract addresses.
2. ``FtsoV2`` (retrieved from the registry) exposes ``getFeedById(bytes21)``
   which returns ``(uint256 value, int8 decimals, uint64 timestamp)``.
3. Actual price = ``value * 10 ** decimals``  (decimals is typically negative).

Feed ID encoding (bytes21)
--------------------------
The first byte is the asset category (0x01 = Crypto).
The remaining 20 bytes are the feed name in ASCII, right-padded with zeros.

    encode_feed_id("FLR/USD") → b'\\x01FLR/USD' + b'\\x00' * 13

Supported feeds (extend ``FEED_IDS`` as needed)
------------------------------------------------
- ``FLR/USD``
- ``SGB/USD``
- ``BTC/USD``
- ``ETH/USD``
- ``XRP/USD``
- ``USDC/USD``
- ``USDT/USD``

Usage
-----
    from app.flare.ftso import get_ftso_rate, get_ftso_rates

    rate = get_ftso_rate("FLR/USD")
    if rate:
        print(rate.value)        # Decimal("0.02150")
        print(rate.timestamp)    # 1706000000
        print(rate.source)       # "ftso_v2"

    rates = get_ftso_rates(["FLR/USD", "BTC/USD"])

Environment variables
---------------------
``FLARE_RPC_URL``          – Flare C-Chain RPC (default: public Flare endpoint)
``FTSO_CACHE_TTL``         – Seconds to cache a feed value (default: 90)
``FTSO_REGISTRY_ADDRESS``  – Override contract registry address (rarely needed)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

try:
    from cachetools import TTLCache  # type: ignore
except Exception:  # pragma: no cover
    TTLCache = None  # type: ignore

try:
    from web3 import Web3  # type: ignore
except Exception:  # pragma: no cover
    Web3 = None  # type: ignore

import logging

logger = logging.getLogger("middleware.flare.ftso")

# ── Contract addresses ────────────────────────────────────────────────────────

# Stable registry deployed by Flare Foundation — only changes with major
# network upgrades. Override via env if needed.
FLARE_CONTRACT_REGISTRY = os.getenv(
    "FTSO_REGISTRY_ADDRESS",
    "0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019",
)

# ── ABIs (minimal) ────────────────────────────────────────────────────────────

_REGISTRY_ABI = [
    {
        "inputs": [{"name": "_name", "type": "string"}],
        "name": "getContractAddressByName",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    }
]

_FTSO_V2_ABI = [
    {
        "inputs": [{"name": "_feedId", "type": "bytes21"}],
        "name": "getFeedById",
        "outputs": [
            {"name": "_value", "type": "uint256"},
            {"name": "_decimals", "type": "int8"},
            {"name": "_timestamp", "type": "uint64"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "_feedIds", "type": "bytes21[]"}],
        "name": "getFeedsById",
        "outputs": [
            {"name": "_values", "type": "uint256[]"},
            {"name": "_decimals", "type": "int8[]"},
            {"name": "_timestamp", "type": "uint64"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

# ── Feed ID catalogue ─────────────────────────────────────────────────────────
# Category byte 0x01 = Crypto. Name is ASCII right-padded to 20 bytes.
# To add a feed: FEED_IDS["NEW/USD"] = encode_feed_id("NEW/USD")

def _encode_feed_id(symbol: str) -> bytes:
    """Encode a feed symbol into a bytes21 feed ID."""
    name = symbol.encode("ascii")
    if len(name) > 20:
        raise ValueError(f"Feed symbol too long: {symbol!r}")
    return b"\x01" + name.ljust(20, b"\x00")


FEED_IDS: Dict[str, bytes] = {
    sym: _encode_feed_id(sym)
    for sym in [
        "FLR/USD",
        "SGB/USD",
        "BTC/USD",
        "ETH/USD",
        "XRP/USD",
        "USDC/USD",
        "USDT/USD",
        "ADA/USD",
        "DOGE/USD",
        "ALGO/USD",
    ]
}

# ── Cache ─────────────────────────────────────────────────────────────────────

_CACHE_TTL = int(os.getenv("FTSO_CACHE_TTL", "90"))
_cache: Optional[TTLCache] = TTLCache(maxsize=128, ttl=_CACHE_TTL) if TTLCache else None  # type: ignore

# Module-level cache for the resolved FtsoV2 address (changes only on upgrades)
_ftso_v2_address: Optional[str] = None


# ── Data class ────────────────────────────────────────────────────────────────

@dataclass
class FTSORate:
    """A single price feed result from the FTSO v2 oracle."""

    feed_id: str           # e.g. "FLR/USD"
    value: Decimal         # Human-readable price, e.g. Decimal("0.02150")
    raw_value: int         # On-chain uint256 before decimal scaling
    raw_decimals: int      # int8 exponent: actual_price = raw_value * 10**raw_decimals
    timestamp: int         # Unix epoch when the feed was last updated on-chain
    source: str = "ftso_v2"

    @property
    def age_seconds(self) -> float:
        import time
        return time.time() - self.timestamp


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_web3(rpc_url: Optional[str] = None) -> Optional[object]:
    if Web3 is None:
        return None
    url = rpc_url or os.getenv("FLARE_RPC_URL", "https://flare-api.flare.network/ext/C/rpc")
    return Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 10}))


def _resolve_ftso_v2_address(w3, rpc_url: Optional[str] = None) -> Optional[str]:
    """Look up the live FtsoV2 address from the contract registry."""
    global _ftso_v2_address
    if _ftso_v2_address:
        return _ftso_v2_address
    try:
        registry = w3.eth.contract(
            address=Web3.to_checksum_address(FLARE_CONTRACT_REGISTRY),
            abi=_REGISTRY_ABI,
        )
        addr = registry.functions.getContractAddressByName("FtsoV2").call()
        if addr and addr != "0x" + "0" * 40:
            _ftso_v2_address = addr
            logger.info("ftso_v2_resolved address=%s", addr)
            return addr
    except Exception as exc:
        logger.debug("ftso_registry_lookup_failed: %s", exc)
    return None


def _decode_feed_result(raw_value: int, raw_decimals: int) -> Decimal:
    """Convert (uint256, int8) → human-readable Decimal."""
    return Decimal(raw_value) * Decimal(10) ** int(raw_decimals)


# ── Public API ────────────────────────────────────────────────────────────────

def get_ftso_rate(
    feed_symbol: str,
    rpc_url: Optional[str] = None,
) -> Optional[FTSORate]:
    """Fetch a single price feed from Flare FTSO v2.

    Returns ``None`` if the network is unreachable, web3 is unavailable, or
    the feed symbol is not registered in ``FEED_IDS``.

    Results are cached for ``FTSO_CACHE_TTL`` seconds (default 90 s).
    """
    if Web3 is None:
        logger.debug("ftso_unavailable: web3 not installed")
        return None

    feed_id_bytes = FEED_IDS.get(feed_symbol)
    if feed_id_bytes is None:
        logger.debug("ftso_unknown_feed: %s", feed_symbol)
        return None

    cache_key = ("ftso_v2", feed_symbol)
    if _cache is not None:
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

    try:
        w3 = _get_web3(rpc_url)
        if w3 is None:
            return None

        ftso_addr = _resolve_ftso_v2_address(w3, rpc_url)
        if not ftso_addr:
            logger.warning("ftso_v2_address_unresolved")
            return None

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(ftso_addr),
            abi=_FTSO_V2_ABI,
        )

        raw_value, raw_decimals, timestamp = contract.functions.getFeedById(
            feed_id_bytes
        ).call()

        rate = FTSORate(
            feed_id=feed_symbol,
            value=_decode_feed_result(raw_value, raw_decimals),
            raw_value=int(raw_value),
            raw_decimals=int(raw_decimals),
            timestamp=int(timestamp),
        )

        if _cache is not None:
            _cache[cache_key] = rate

        logger.info(
            "ftso_rate feed=%s value=%s ts=%s",
            feed_symbol,
            rate.value,
            timestamp,
        )
        return rate

    except Exception as exc:
        logger.debug("ftso_rate_fetch_failed feed=%s: %s", feed_symbol, exc)
        return None


def get_ftso_rates(
    feed_symbols: List[str],
    rpc_url: Optional[str] = None,
) -> Dict[str, Optional[FTSORate]]:
    """Fetch multiple feeds in a single batched RPC call where possible.

    Returns a dict ``{feed_symbol: FTSORate | None}``.
    Falls back to individual ``getFeedById`` calls if ``getFeedsById`` fails.
    """
    if Web3 is None:
        return {sym: None for sym in feed_symbols}

    results: Dict[str, Optional[FTSORate]] = {}

    # Check cache first; collect what needs fetching
    missing: List[str] = []
    for sym in feed_symbols:
        cache_key = ("ftso_v2", sym)
        if _cache is not None and cache_key in _cache:
            results[sym] = _cache[cache_key]
        else:
            missing.append(sym)

    if not missing:
        return results

    try:
        w3 = _get_web3(rpc_url)
        if w3 is None:
            for sym in missing:
                results[sym] = None
            return results

        ftso_addr = _resolve_ftso_v2_address(w3, rpc_url)
        if not ftso_addr:
            for sym in missing:
                results[sym] = None
            return results

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(ftso_addr),
            abi=_FTSO_V2_ABI,
        )

        valid = [(sym, FEED_IDS[sym]) for sym in missing if sym in FEED_IDS]
        if not valid:
            for sym in missing:
                results[sym] = None
            return results

        syms, feed_ids = zip(*valid)

        try:
            # Batched call
            values, decimals_list, timestamp = contract.functions.getFeedsById(
                list(feed_ids)
            ).call()
            for sym, raw_value, raw_dec in zip(syms, values, decimals_list):
                rate = FTSORate(
                    feed_id=sym,
                    value=_decode_feed_result(raw_value, raw_dec),
                    raw_value=int(raw_value),
                    raw_decimals=int(raw_dec),
                    timestamp=int(timestamp),
                )
                results[sym] = rate
                if _cache is not None:
                    _cache[("ftso_v2", sym)] = rate

        except Exception:
            # Fallback: individual calls
            for sym in syms:
                results[sym] = get_ftso_rate(sym, rpc_url)

    except Exception as exc:
        logger.debug("ftso_batch_failed: %s", exc)
        for sym in missing:
            results[sym] = None

    return results


def ftso_rate_as_str(feed_symbol: str, places: int = 8) -> Optional[str]:
    """Convenience: return the FTSO rate as a normalized decimal string or None."""
    rate = get_ftso_rate(feed_symbol)
    if rate is None or rate.value <= 0:
        return None
    from decimal import ROUND_HALF_EVEN
    q = Decimal(10) ** (-places)
    s = format(rate.value.quantize(q, rounding=ROUND_HALF_EVEN), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def symbol_to_feed(currency: str) -> Optional[str]:
    """Map a currency code to its FTSO feed ID symbol (e.g. 'FLR' → 'FLR/USD')."""
    candidate = f"{currency.upper()}/USD"
    return candidate if candidate in FEED_IDS else None
