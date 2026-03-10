from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple

# External integrations are optional and must never break the flow
try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

try:
    from cachetools import TTLCache  # type: ignore
except Exception:  # pragma: no cover
    TTLCache = None  # type: ignore

try:
    from web3 import Web3  # type: ignore
except Exception:  # pragma: no cover
    Web3 = None  # type: ignore


# Minimal FX provider facade with real Coingecko client + optional Chainlink reader.
# Returns a stringified decimal rate or None if unavailable. Caches are best-effort.

# Coingecko symbol -> id mapping (override via env, e.g., COINGECKO_ID_FLR)
COINGECKO_IDS: Dict[str, str] = {
    "FLR": os.getenv("COINGECKO_ID_FLR", "flare-networks"),
}
# Common base currencies mapping to Coingecko vs_currencies keys
COINGECKO_BASES: Dict[str, str] = {
    "USD": "usd",
    "EUR": "eur",
    "GBP": "gbp",
}

# TTL cache for HTTP quotes (60s default)
_cache_ttl = int(os.getenv("FX_CACHE_TTL", "60"))
_cache = TTLCache(maxsize=256, ttl=_cache_ttl) if TTLCache else None

# Minimal Chainlink AggregatorV3 interface
AGGREGATORV3_ABI = [
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "latestRoundData",
        "outputs": [
            {"internalType": "uint80", "name": "roundId", "type": "uint80"},
            {"internalType": "int256", "name": "answer", "type": "int256"},
            {"internalType": "uint256", "name": "startedAt", "type": "uint256"},
            {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
            {"internalType": "uint80", "name": "answeredInRound", "type": "uint80"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


def _normalize_decimal(val: Any, places: int = 8) -> Optional[str]:
    try:
        d = Decimal(str(val))
        if d <= 0:
            return None
        q = Decimal(10) ** (-places)
        # quantize then strip trailing zeros
        s = format(d.quantize(q), "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
    except (InvalidOperation, ValueError, TypeError):
        return None


def _cache_get(key: Tuple[Any, ...]) -> Optional[str]:
    if _cache is None:
        return None
    try:
        return _cache.get(key)
    except Exception:
        return None


def _cache_set(key: Tuple[Any, ...], value: str) -> None:
    if _cache is None:
        return
    try:
        _cache[key] = value
    except Exception:
        pass


def _coingecko_rate(base_ccy: Optional[str], quote_ccy: Optional[str]) -> Optional[str]:
    if not requests:
        return None
    if not quote_ccy:
        return None
    base = (base_ccy or "USD").upper()
    vs = COINGECKO_BASES.get(base, base.lower())
    sym = quote_ccy.upper().strip()
    asset_id = COINGECKO_IDS.get(sym)
    if not asset_id:
        return None

    key = ("coingecko", vs, asset_id)
    cached = _cache_get(key)
    if cached:
        return cached

    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={asset_id}&vs_currencies={vs}"
        r = requests.get(url, timeout=10)
        if r.ok:
            data = r.json()
            raw = data.get(asset_id, {}).get(vs)
            s = _normalize_decimal(raw)
            if s:
                _cache_set(key, s)
                return s
    except Exception:
        return None
    return None


def get_chainlink_rate(rpc_url: Optional[str], aggregator_address: Optional[str]) -> Optional[str]:
    """
    Read latest answer from Chainlink AggregatorV3 and normalize by decimals.
    rpc_url: HTTP RPC URL for the network
    aggregator_address: aggregator contract address
    """
    if not rpc_url or not aggregator_address:
        return None
    if Web3 is None:
        return None
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
        contract = w3.eth.contract(address=Web3.to_checksum_address(aggregator_address), abi=AGGREGATORV3_ABI)
        decimals = int(contract.functions.decimals().call())
        roundData = contract.functions.latestRoundData().call()
        answer = roundData[1]
        # Chainlink answers are int256
        if answer is None or int(answer) <= 0:
            return None
        d = Decimal(int(answer)) / (Decimal(10) ** decimals)
        return _normalize_decimal(d)
    except Exception:
        return None


def _chainlink_rate_from_env() -> Optional[str]:
    """
    Convenience helper when feed/rpc are provided via env:
      CHAINLINK_FEED, CHAINLINK_RPC_URL
    """
    feed = os.getenv("CHAINLINK_FEED")
    rpc = os.getenv("CHAINLINK_RPC_URL")
    return get_chainlink_rate(rpc, feed)


def get_rate(base_ccy: Optional[str], quote_ccy: Optional[str], provider: Optional[str]) -> Optional[str]:
    """
    Public facade preserved for backward compatibility.
    provider: 'coingecko' | 'chainlink' | other
    """
    if not quote_ccy or not provider:
        return None
    p = provider.lower().strip()
    try:
        if p == "coingecko":
            return _coingecko_rate(base_ccy, quote_ccy)
        elif p == "chainlink":
            # Use env-configured feed/rpc by default.
            return _chainlink_rate_from_env()
        else:
            return None
    except Exception:
        return None


def get_rate_detail(
    base_ccy: Optional[str],
    quote_ccy: Optional[str],
    provider: Optional[str],
    *,
    rpc_url: Optional[str] = None,
    feed: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """
    Extended variant that returns {'rate': str|None, 'source': 'coingecko'|'chainlink'|None}.
    Allows passing Chainlink parameters explicitly without env.
    """
    src = None
    rate: Optional[str] = None
    p = (provider or "").lower().strip()
    if p == "coingecko":
        src = "coingecko"
        rate = _coingecko_rate(base_ccy, quote_ccy)
    elif p == "chainlink":
        src = "chainlink"
        if rpc_url or feed:
            rate = get_chainlink_rate(rpc_url, feed)
        else:
            rate = _chainlink_rate_from_env()
    return {"rate": rate, "source": src}
