"""ISO Middleware Client."""

from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests


class ISOClient:
    """Client for ISO 20022 Middleware API."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None, timeout: int = 30):
        """Initialize the ISO client.

        Args:
            base_url: Base URL of the middleware API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if extra:
            headers.update(extra)
        return headers

    def _url(self, path: str) -> str:
        """Build full URL for a path."""
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def list_receipts(
        self,
        status: Optional[str] = None,
        chain: Optional[str] = None,
        reference: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        scope: str = "mine",
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """List receipts with optional filters."""
        params = {
            "page": page,
            "page_size": page_size,
            "scope": scope,
        }
        if status:
            params["status"] = status
        if chain:
            params["chain"] = chain
        if reference:
            params["reference"] = reference
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        response = requests.get(
            self._url("/v1/receipts"),
            params={k: v for k, v in params.items() if v is not None},
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_receipt(self, receipt_id: str) -> Dict[str, Any]:
        """Get a specific receipt by ID."""
        response = requests.get(
            self._url(f"/v1/iso/receipts/{receipt_id}"),
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_anchors(self, receipt_id: str) -> list[Dict[str, Any]]:
        """Get per-chain anchor txids for a receipt."""
        response = requests.get(
            self._url(f"/v1/anchors/{receipt_id}"),
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def confirm_anchor(self, receipt_id: str, flare_txid: str, chain: Optional[str] = None) -> Dict[str, Any]:
        """Confirm anchoring for a receipt (tenant/self-hosted mode)."""
        payload: Dict[str, Any] = {"receipt_id": receipt_id, "flare_txid": flare_txid}
        if chain:
            payload["chain"] = chain
        response = requests.post(
            self._url("/v1/iso/confirm-anchor"),
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_project_config(self, project_id: str) -> Dict[str, Any]:
        """Get project anchoring config (execution_mode + chains)."""
        response = requests.get(
            self._url(f"/v1/projects/{project_id}/config"),
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def put_project_config(self, project_id: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Update project anchoring config (execution_mode + chains)."""
        response = requests.put(
            self._url(f"/v1/projects/{project_id}/config"),
            json=cfg,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def verify_bundle(self, bundle_url: Optional[str] = None, bundle_hash: Optional[str] = None) -> Dict[str, Any]:
        """Verify a bundle (by URL or hash)."""
        payload: Dict[str, Any] = {}
        if bundle_url:
            payload["bundle_url"] = bundle_url
        if bundle_hash:
            payload["bundle_hash"] = bundle_hash

        response = requests.post(
            self._url("/v1/iso/verify"),
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def verify_cid(self, cid: str, store: str = "auto", receipt_id: Optional[str] = None) -> Dict[str, Any]:
        """Verify a CID (IPFS/Arweave)."""
        payload: Dict[str, Any] = {"cid": cid, "store": store}
        if receipt_id:
            payload["receipt_id"] = receipt_id

        response = requests.post(
            self._url("/v1/iso/verify-cid"),
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def camt053(self, date: str) -> Dict[str, Any]:
        """Generate camt.053 statement for a date."""
        response = requests.get(
            self._url("/v1/iso/statements/camt053"),
            params={"date": date},
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def camt052(self, date: str, window: str = "1h") -> Dict[str, Any]:
        """Generate camt.052 intraday statement."""
        response = requests.get(
            self._url("/v1/iso/statements/camt052"),
            params={"date": date, "window": window},
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def ai_status(self) -> Dict[str, Any]:
        """Get AI provider status."""
        response = requests.get(
            self._url("/v1/ai/status"),
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def auth_me(self) -> Dict[str, Any]:
        """Get current principal information."""
        response = requests.get(
            self._url("/v1/auth/me"),
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def refund(self, original_receipt_id: str, reason_code: Optional[str] = None) -> Dict[str, Any]:
        """Initiate a refund/return for an existing receipt.
        
        Args:
            original_receipt_id: The receipt ID to refund
            reason_code: Optional ISO reason code (e.g., 'CUST', 'DUPL', 'TECH', 'FRAD')
            
        Returns:
            Dictionary with refund_receipt_id and status
        """
        payload: Dict[str, Any] = {"original_receipt_id": original_receipt_id}
        if reason_code:
            payload["reason_code"] = reason_code
            
        response = requests.post(
            self._url("/v1/iso/refund"),
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
