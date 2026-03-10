"""Storage backends for evidence bundles.

Supports local, IPFS, and Arweave storage modes.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

import requests


class StorageBackend:
    """Base class for storage backends."""

    def upload(self, file_path: str) -> Optional[str]:
        """Upload a file and return an identifier (CID, txid, URL)."""
        raise NotImplementedError

    def download(self, identifier: str) -> Optional[bytes]:
        """Download a file by identifier."""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """Local filesystem storage (default)."""

    def __init__(self, artifacts_dir: str = "artifacts"):
        self.artifacts_dir = Path(artifacts_dir)

    def upload(self, file_path: str) -> Optional[str]:
        """For local storage, upload is a no-op. File already exists locally."""
        return str(Path(file_path).relative_to(self.artifacts_dir))

    def download(self, identifier: str) -> Optional[bytes]:
        """Read file from local filesystem."""
        try:
            file_path = self.artifacts_dir / identifier
            return file_path.read_bytes()
        except Exception:
            return None


class IPFSStorage(StorageBackend):
    """IPFS storage via web3.storage or custom gateway.
    
    Configuration:
        IPFS_TOKEN: API token for web3.storage
        IPFS_GATEWAY: Optional custom gateway URL (default: https://w3s.link/ipfs/)
    """

    def __init__(self, token: Optional[str] = None, gateway: Optional[str] = None):
        self.token = token or os.getenv("IPFS_TOKEN")
        self.gateway = gateway or os.getenv("IPFS_GATEWAY", "https://w3s.link/ipfs/")
        self.upload_url = "https://api.web3.storage/upload"

    def upload(self, file_path: str) -> Optional[str]:
        """Upload file to IPFS via web3.storage.
        
        Returns:
            CID string (e.g., 'bafybeig...') or None on failure
        """
        if not self.token:
            return None

        try:
            with open(file_path, "rb") as f:
                response = requests.post(
                    self.upload_url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/octet-stream",
                    },
                    data=f,
                    timeout=60,
                )

            if response.ok:
                data = response.json()
                # web3.storage returns 'cid' or 'carCid'
                cid = data.get("cid") or data.get("carCid")
                return cid
            else:
                return None

        except Exception:
            return None

    def download(self, cid: str) -> Optional[bytes]:
        """Download file from IPFS gateway.
        
        Args:
            cid: IPFS CID (Qm... or bafy...)
            
        Returns:
            File bytes or None on failure
        """
        if not cid:
            return None

        try:
            gateway_url = f"{self.gateway.rstrip('/')}/{cid}"
            response = requests.get(gateway_url, timeout=30)
            if response.ok:
                return response.content
            return None
        except Exception:
            return None


class ArweaveStorage(StorageBackend):
    """Arweave permanent storage via Bundlr or turbo.
    
    Configuration:
        ARWEAVE_POST_URL: Upload endpoint (e.g., https://node2.bundlr.network/tx)
        BUNDLR_AUTH: Authorization token for uploads
        ARWEAVE_GATEWAY: Gateway URL (default: https://arweave.net/)
    """

    def __init__(
        self,
        post_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        gateway: Optional[str] = None,
    ):
        self.post_url = post_url or os.getenv("ARWEAVE_POST_URL")
        self.auth_token = auth_token or os.getenv("BUNDLR_AUTH")
        self.gateway = gateway or os.getenv("ARWEAVE_GATEWAY", "https://arweave.net/")

    def upload(self, file_path: str) -> Optional[str]:
        """Upload file to Arweave via Bundlr/turbo.
        
        Returns:
            Transaction ID or None on failure
        """
        if not self.post_url or not self.auth_token:
            return None

        try:
            with open(file_path, "rb") as f:
                response = requests.post(
                    self.post_url,
                    headers={
                        "Authorization": f"Bearer {self.auth_token}",
                        "Content-Type": "application/octet-stream",
                    },
                    data=f,
                    timeout=60,
                )

            if response.ok:
                data = response.json()
                # Bundlr/turbo return 'id' or 'txid'
                txid = data.get("id") or data.get("txid")
                if isinstance(txid, str) and txid:
                    return txid
            return None

        except Exception:
            return None

    def download(self, txid: str) -> Optional[bytes]:
        """Download file from Arweave gateway.
        
        Args:
            txid: Arweave transaction ID
            
        Returns:
            File bytes or None on failure
        """
        if not txid:
            return None

        try:
            gateway_url = f"{self.gateway.rstrip('/')}/{txid}"
            response = requests.get(gateway_url, timeout=30)
            if response.ok:
                return response.content
            return None
        except Exception:
            return None


def get_storage_backend(mode: str = "local") -> StorageBackend:
    """Factory function to get the appropriate storage backend.
    
    Args:
        mode: Storage mode ('local', 'ipfs', 'arweave')
        
    Returns:
        StorageBackend instance
    """
    mode = (mode or "local").lower()

    if mode == "ipfs":
        return IPFSStorage()
    elif mode == "arweave":
        return ArweaveStorage()
    else:
        # Default to local
        artifacts_dir = os.getenv("ARTIFACTS_DIR", "artifacts")
        return LocalStorage(artifacts_dir)


def upload_bundle(file_path: str, mode: str = "local") -> Tuple[Optional[str], str]:
    """Upload bundle to configured storage backend.
    
    Args:
        file_path: Path to the evidence bundle ZIP file
        mode: Storage mode ('local', 'ipfs', 'arweave')
        
    Returns:
        Tuple of (identifier, mode) where identifier is CID/txid/path
    """
    backend = get_storage_backend(mode)
    identifier = backend.upload(file_path)
    return identifier, mode


def download_bundle(identifier: str, mode: str = "auto") -> Optional[bytes]:
    """Download bundle from storage.
    
    Args:
        identifier: CID, txid, or local path
        mode: Storage mode ('auto', 'local', 'ipfs', 'arweave')
        
    Returns:
        File bytes or None on failure
    """
    # Auto-detect mode from identifier format
    if mode == "auto":
        if identifier.startswith("Qm") or identifier.startswith("bafy"):
            mode = "ipfs"
        elif len(identifier) == 43 and not identifier.startswith("0x"):
            # Arweave TXIDs are 43 chars base64url
            mode = "arweave"
        else:
            mode = "local"

    backend = get_storage_backend(mode)
    return backend.download(identifier)


def save_storage_metadata(receipt_dir: Path, identifier: Optional[str], mode: str) -> None:
    """Save storage metadata to receipt directory.
    
    Args:
        receipt_dir: Receipt artifacts directory
        identifier: CID, txid, or path
        mode: Storage mode
    """
    if not identifier:
        return

    try:
        if mode == "ipfs":
            (receipt_dir / "cid.txt").write_text(identifier)
        elif mode == "arweave":
            (receipt_dir / "arweave_txid.txt").write_text(identifier)
        elif mode == "local":
            # Local mode doesn't need extra metadata
            pass
    except Exception:
        pass


# Documentation for environment variables
"""
Storage Backend Environment Variables:

Local Storage (default):
  ARTIFACTS_DIR=artifacts

IPFS Storage:
  IPFS_TOKEN=<web3.storage API token>
  IPFS_GATEWAY=https://w3s.link/ipfs/  (optional, custom gateway)

Arweave Storage:
  ARWEAVE_POST_URL=https://node2.bundlr.network/tx  (upload endpoint)
  BUNDLR_AUTH=<bundlr/turbo auth token>
  ARWEAVE_GATEWAY=https://arweave.net/  (optional, custom gateway)

Usage in OrgConfig:
  {
    "evidence": {
      "store": {
        "mode": "local|ipfs|arweave",
        "files_base": "https://cdn.example.com"  (optional CDN prefix)
      }
    }
  }

Notes:
- IPFS: Best for public, content-addressed storage with low friction
- Arweave: Best for permanent, immutable storage (higher cost, better durability)
- Local: Default mode, serves via /files/{id} endpoint
- Hybrid: You can upload to IPFS/Arweave and still serve via local files
"""
