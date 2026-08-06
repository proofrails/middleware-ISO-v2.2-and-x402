"""x402 premium endpoint tests — in-process, no external server required.

These tests verify payment gating behaviour. Because on-chain verification
requires a live RPC, payment verification tests use X402_MOCK_PAYMENTS=true
(set in conftest.py via monkeypatch) to exercise the guard logic without a
real blockchain connection.
"""
from __future__ import annotations

import json
import os

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

# Tuples of (method, path, body) — bodies must be schema-valid so FastAPI
# does not return 422 before the payment guard runs.
PREMIUM_ENDPOINTS = [
    ("POST", "/v1/x402/premium/verify-bundle",      {"bundle_hash": "0x" + "a" * 64}),
    ("POST", "/v1/x402/premium/generate-statement", {"date": "2026-01-01"}),
    ("POST", "/v1/x402/premium/fx-lookup",          {"base_ccy": "USD", "quote_ccy": "FLR", "provider": "fallback"}),
    ("POST", "/v1/x402/premium/bulk-verify",        {"bundle_urls": ["http://example.com/bundle.zip"]}),
    ("POST", "/v1/x402/premium/refund",             {"original_receipt_id": "00000000-0000-0000-0000-000000000001"}),
]

MOCK_PAYMENT_HEADER = json.dumps({
    "tx_hash": "0xdead000000000000000000000000000000000000000000000000000000000001",
    "amount": "0.001",
    "recipient": "0x0690d8cFb1897c12B2C0b34660edBDE4E20ff4d8",
    "currency": "USDC",
    "chain": "base",
})


# ── Payment gating ────────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.parametrize("method,path,body", PREMIUM_ENDPOINTS)
def test_premium_endpoint_returns_402_without_payment(client, method, path, body):
    """Every premium endpoint must return HTTP 402 when no X-PAYMENT header is present."""
    resp = client.post(path, json=body) if method == "POST" else client.get(path)
    assert resp.status_code == 402, (
        f"{path} returned {resp.status_code} instead of 402 — payment gate may not be active"
    )


@pytest.mark.unit
@pytest.mark.parametrize("method,path,body", PREMIUM_ENDPOINTS)
def test_premium_endpoint_402_body_has_accepted_field(client, method, path, body):
    """402 response must include an 'accepted' list with payment options."""
    resp = client.post(path, json=body) if method == "POST" else client.get(path)
    assert resp.status_code == 402
    data = resp.json()
    assert "accepted" in data, f"Missing 'accepted' field in 402 response for {path}"
    assert isinstance(data["accepted"], list)
    assert len(data["accepted"]) >= 1
    option = data["accepted"][0]
    assert "amount" in option
    assert "currency" in option
    assert "recipient" in option


@pytest.mark.unit
@pytest.mark.parametrize("method,path,body", PREMIUM_ENDPOINTS)
def test_premium_endpoint_402_headers(client, method, path, body):
    """402 response must include X-Payment-Required header."""
    resp = client.post(path, json=body) if method == "POST" else client.get(path)
    assert resp.status_code == 402
    assert resp.headers.get("x-payment-required") == "true"


@pytest.mark.unit
def test_invalid_payment_header_returns_400(client, monkeypatch):
    """Malformed X-PAYMENT header should return 400, not 500."""
    monkeypatch.setenv("X402_MOCK_PAYMENTS", "false")
    resp = client.post(
        "/v1/x402/premium/verify-bundle",
        json={"bundle_hash": "0xabc"},
        headers={"X-PAYMENT": "not-valid-json"},
    )
    assert resp.status_code == 400


@pytest.mark.unit
def test_mock_payment_accepted_when_env_set(client, monkeypatch):
    """With X402_MOCK_PAYMENTS=true, any X-PAYMENT header bypasses on-chain check."""
    monkeypatch.setenv("X402_MOCK_PAYMENTS", "true")
    # Reload the module constant (it reads at import time)
    import importlib
    import app.api.routes.x402_premium as mod
    importlib.reload(mod)

    resp = client.post(
        "/v1/x402/premium/fx-lookup",
        json={"base_ccy": "USD", "quote_ccy": "FLR", "provider": "fallback"},
        headers={"X-PAYMENT": MOCK_PAYMENT_HEADER},
    )
    # Should not return 402 or 403 — may return 200 or 503 (if FX provider unavailable)
    assert resp.status_code not in (402, 403), (
        f"Mock mode not bypassing payment gate: {resp.status_code} {resp.text}"
    )


# ── x402 config / analytics endpoints ────────────────────────────────────────

@pytest.mark.unit
def test_get_pricing_returns_list(client):
    resp = client.get("/v1/x402/pricing")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.unit
def test_list_payments_requires_auth(client):
    resp = client.get("/v1/x402/payments")
    assert resp.status_code in (401, 403)


@pytest.mark.unit
def test_revenue_requires_admin(client, admin_headers):
    resp = client.get("/v1/x402/revenue?days=7", headers=admin_headers)
    # Admin should be able to access, or at least not 404
    assert resp.status_code != 404


# ── Pricing routes registered ─────────────────────────────────────────────────

@pytest.mark.unit
def test_x402_routes_in_openapi(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    expected = [
        "/v1/x402/pricing",
        "/v1/x402/payments",
        "/v1/x402/premium/verify-bundle",
        "/v1/x402/premium/generate-statement",
        "/v1/x402/premium/fx-lookup",
        "/v1/x402/premium/bulk-verify",
        "/v1/x402/premium/refund",
    ]
    missing = [p for p in expected if p not in paths]
    assert not missing, f"Missing x402 routes in OpenAPI: {missing}"
