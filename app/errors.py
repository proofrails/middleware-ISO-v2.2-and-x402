from __future__ import annotations

"""Structured error codes for machine-readable API responses.

Every error from this middleware follows the same envelope:
  { "error": { "code": "ERROR_CODE", "message": "...", "retryable": bool, "details": {...} } }

Agentic clients should branch on `code`, not on `message` (which is human text).
"""

from enum import Enum
from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    # Receipt lifecycle
    RECEIPT_NOT_FOUND = "RECEIPT_NOT_FOUND"
    DUPLICATE_TRANSACTION = "DUPLICATE_TRANSACTION"
    DUPLICATE_REFERENCE = "DUPLICATE_REFERENCE"
    RECEIPT_NOT_FAILED = "RECEIPT_NOT_FAILED"
    RECEIPT_NO_BUNDLE = "RECEIPT_NO_BUNDLE"

    # Anchor
    ANCHOR_TIMEOUT = "ANCHOR_TIMEOUT"
    ANCHOR_FAILED = "ANCHOR_FAILED"
    ANCHOR_CONFLICT = "ANCHOR_CONFLICT"

    # Auth
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"

    # Payment / x402
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    PAYMENT_VERIFICATION_FAILED = "PAYMENT_VERIFICATION_FAILED"

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_CHAIN = "INVALID_CHAIN"

    # Rate limiting
    RATE_LIMITED = "RATE_LIMITED"

    # Idempotency
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"

    # Webhooks
    WEBHOOK_NOT_FOUND = "WEBHOOK_NOT_FOUND"
    WEBHOOK_LIMIT_REACHED = "WEBHOOK_LIMIT_REACHED"

    # Operations
    OPERATION_NOT_FOUND = "OPERATION_NOT_FOUND"

    # Flare / FTSO / FDC
    FTSO_UNAVAILABLE = "FTSO_UNAVAILABLE"
    FEED_NOT_FOUND = "FEED_NOT_FOUND"
    FDC_ATTESTATION_FAILED = "FDC_ATTESTATION_FAILED"

    # Generic
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"


class APIError(Exception):
    """Raised to return a structured error response to the caller.

    Example usage inside a route:
        raise APIError(ErrorCode.RECEIPT_NOT_FOUND, f"Receipt '{rid}' not found", 404)

    The registered exception handler converts this into the standard envelope.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 400,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.details:
            body["details"] = self.details
        return {"error": body}


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


# ── Convenience constructors ──────────────────────────────────────────────────

def receipt_not_found(rid: str) -> APIError:
    return APIError(ErrorCode.RECEIPT_NOT_FOUND, f"Receipt '{rid}' not found", 404)


def not_found(resource: str, rid: Optional[str] = None) -> APIError:
    msg = f"{resource} '{rid}' not found" if rid else f"{resource} not found"
    return APIError(ErrorCode.NOT_FOUND, msg, 404)


def unauthorized(msg: str = "Authentication required") -> APIError:
    return APIError(ErrorCode.UNAUTHORIZED, msg, 401)


def rate_limited(retry_after: int = 60) -> APIError:
    return APIError(
        ErrorCode.RATE_LIMITED,
        "Rate limit exceeded",
        429,
        retryable=True,
        details={"retry_after_seconds": retry_after},
    )
