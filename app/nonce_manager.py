from __future__ import annotations

import logging
import re

from redis import Redis  # type: ignore
from web3 import Web3  # type: ignore

logger = logging.getLogger(__name__)

_NONCE_TOO_LOW_RE = re.compile(r"next nonce (\d+)")

# Redis key used to store the next nonce atomically across forked workers
_REDIS_KEY = "anchor:nonce:{address}"


class NonceManager:
    """Redis-backed nonce counter for a single wallet.

    RQ forks a new process for each job, so an in-memory counter loses
    state across jobs.  This version stores the nonce in Redis and uses
    INCR for atomic, cross-fork coordination.
    """

    def __init__(self, w3: Web3, address: str, redis: Redis | None = None):
        self._w3 = w3
        self._address = address
        self._redis: Redis | None = redis
        self._key = _REDIS_KEY.format(address=address.lower())
        # Fallback for environments without Redis (shouldn't happen in prod)
        self._next: int | None = None

    def _get_redis(self) -> Redis:
        if self._redis is None:
            from .queue import get_redis
            self._redis = get_redis()
        return self._redis

    def next(self) -> int:
        """Return the next nonce and atomically increment the counter."""
        try:
            r = self._get_redis()
            # If the key doesn't exist yet, seed it from chain
            if not r.exists(self._key):
                self.reset()
            # INCR returns the value *after* incrementing, so we store
            # "next nonce to use" and do GET-then-INCR via a Lua script
            # to make the read-and-increment atomic.
            n = self._atomic_next(r)
            logger.debug("nonce_manager_next nonce=%s address=%s", n, self._address)
            return n
        except Exception:
            logger.exception("nonce_manager_redis_error, falling back to chain query")
            return self._fallback_next()

    def _atomic_next(self, r: Redis) -> int:
        """Atomically read current nonce and increment.

        Uses a Lua script so GET + INCR is a single atomic operation.
        """
        lua = """
        local val = redis.call('GET', KEYS[1])
        redis.call('INCR', KEYS[1])
        return val
        """
        result = r.eval(lua, 1, self._key)
        return int(result)

    def _fallback_next(self) -> int:
        """Chain-query fallback if Redis is unavailable."""
        if self._next is None:
            try:
                self._next = self._w3.eth.get_transaction_count(self._address, "pending")
            except Exception:
                self._next = self._w3.eth.get_transaction_count(self._address, "latest")
        n = self._next
        self._next += 1
        return n

    def reset(self, error: BaseException | None = None) -> None:
        """Re-sync nonce from chain (call on startup and after detecting issues).

        If *error* is a "nonce too low" RPC error, the expected nonce is parsed
        from the message so we don't re-query an RPC that returns stale values.
        """
        hint_nonce: int | None = None
        if error is not None:
            m = _NONCE_TOO_LOW_RE.search(str(error))
            if m:
                hint_nonce = int(m.group(1))
                logger.info(
                    "nonce_manager_hint_from_error nonce=%s address=%s",
                    hint_nonce, self._address,
                )

        # Query both pending and latest and take the max — some Flare RPCs
        # don't reliably reflect mempool txs in the "pending" count.
        try:
            pending = self._w3.eth.get_transaction_count(self._address, "pending")
        except Exception:
            pending = 0
        try:
            latest = self._w3.eth.get_transaction_count(self._address, "latest")
        except Exception:
            latest = 0

        chain_nonce = max(pending, latest)

        candidates = [chain_nonce]
        if hint_nonce is not None:
            candidates.append(hint_nonce)

        # Also consider the current Redis value (another fork may have advanced it)
        try:
            r = self._get_redis()
            current = r.get(self._key)
            if current is not None:
                candidates.append(int(current))
        except Exception:
            pass

        new_nonce = max(candidates)

        # Write to Redis
        try:
            r = self._get_redis()
            # Use SET with GET to avoid race: only advance, never go backwards
            lua = """
            local cur = redis.call('GET', KEYS[1])
            if cur == false or tonumber(cur) < tonumber(ARGV[1]) then
                redis.call('SET', KEYS[1], ARGV[1])
                return 1
            end
            return 0
            """
            r.eval(lua, 1, self._key, str(new_nonce))
        except Exception:
            logger.exception("nonce_manager_redis_set_error")

        # Keep local fallback in sync too
        self._next = new_nonce

        logger.info(
            "nonce_manager_reset nonce=%s chain=%s hint=%s address=%s",
            new_nonce, chain_nonce, hint_nonce, self._address,
        )
