from __future__ import annotations

import logging

from web3 import Web3  # type: ignore

logger = logging.getLogger(__name__)


class NonceManager:
    """In-memory nonce counter for a single wallet.

    Designed for a single anchor worker process — no distributed locking needed.
    Lazily initialises from chain on first use, then increments locally.
    """

    def __init__(self, w3: Web3, address: str):
        self._w3 = w3
        self._address = address
        self._next: int | None = None

    def next(self) -> int:
        if self._next is None:
            self.reset()
        n = self._next
        self._next += 1  # type: ignore[operator]
        logger.debug("nonce_manager_next nonce=%s address=%s", n, self._address)
        return n

    def reset(self) -> None:
        """Re-sync nonce from chain (call on startup and after detecting issues)."""
        self._next = self._w3.eth.get_transaction_count(self._address, "pending")
        logger.info("nonce_manager_reset nonce=%s address=%s", self._next, self._address)
