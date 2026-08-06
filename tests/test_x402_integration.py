"""Backend integration tests for x402 multi-payment support.

Uses FastAPI TestClient with mocked chain verification. Does not hit any real RPC.
Tests the full request→402→pay→unlock flow for each payment path.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ── Constants ─────────────────────────────────────────────────────────────────

USDT0 = "0xe7cd86e13AC4309349F30B3435a9d337750fC82D"
FACILITATOR = "0x" + "fa" * 20
RECIPIENT = "0x" + "aa" * 20
PAYER = "0x" + "bb" * 20
SETTLEMENT_TX = "0x" + "cc" * 32
USDC_TX = "0x" + "dd" * 32
FLR_TX = "0x" + "ee" * 32
NONCE = "0x" + "ff" * 32


# ── App fixture ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    """Create a test FastAPI app with minimal env config."""
    import os
    os.environ.setdefault("X402_RECIPIENT_ADDRESS", RECIPIENT)
    os.environ.setdefault("X402_USDT0_RECIPIENT", RECIPIENT)
    os.environ.setdefault("X402_FLR_RECIPIENT", RECIPIENT)
    os.environ.setdefault("X402_BASE_RECIPIENT", RECIPIENT)
    os.environ.setdefault("X402_FLARE_FACILITATOR_ADDRESS", FACILITATOR)
    os.environ.setdefault("X402_USDT0_AMOUNT", "0.001")
    os.environ.setdefault("X402_FLR_AMOUNT", "0.05")
    os.environ.setdefault("X402_USDC_AMOUNT", "0.001")
    os.environ.setdefault("AUTO_CREATE_DB", "1")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test_x402_integration.db")

    from app.settings import get_settings
    get_settings.cache_clear()

    from app.api.app_factory import create_app
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as c:
        yield c


# ── 402 response structure ─────────────────────────────────────────────────────

class TestFourOhTwoResponse:

    def test_premium_endpoint_returns_402_without_payment(self, client):
        resp = client.post("/v1/x402/premium/fx-lookup", json={"base_ccy": "USD"})
        assert resp.status_code == 402
        assert resp.headers.get("X-Payment-Required") == "true"

    def test_402_response_has_version_and_accepts(self, client):
        resp = client.post("/v1/x402/premium/fx-lookup", json={})
        assert resp.status_code == 402
        body = resp.json()
        assert body["version"] == "1.0"
        assert body["error"] == "payment_required"
        assert isinstance(body["accepts"], list)
        assert len(body["accepts"]) >= 1

    def test_402_includes_usdt0_option_when_configured(self, client):
        resp = client.post("/v1/x402/premium/fx-lookup", json={})
        accepts = resp.json()["accepts"]
        usdt0 = [a for a in accepts if a.get("payment_type") == "eip3009_facilitator"]
        assert len(usdt0) == 1
        assert usdt0[0]["token"] == USDT0
        assert usdt0[0]["facilitator"] == FACILITATOR
        assert usdt0[0]["chain_id"] == 14
        assert usdt0[0]["decimals"] == 6
        assert usdt0[0]["network"] == "flare"

    def test_402_includes_flr_option_when_configured(self, client):
        resp = client.post("/v1/x402/premium/fx-lookup", json={})
        accepts = resp.json()["accepts"]
        flr = [a for a in accepts if a.get("payment_type") == "native_transfer"]
        assert len(flr) == 1
        assert flr[0]["asset"] == "FLR"
        assert flr[0]["chain_id"] == 14

    def test_402_includes_usdc_option(self, client):
        resp = client.post("/v1/x402/premium/fx-lookup", json={})
        accepts = resp.json()["accepts"]
        usdc = [a for a in accepts if a.get("payment_type") == "erc20_transfer"]
        assert len(usdc) == 1
        assert usdc[0]["asset"] == "USDC"
        assert usdc[0]["network"] == "base"

    def test_usdt0_hidden_when_toggle_off(self, client):
        import os
        os.environ["X402_ENABLE_FLARE_USDT0"] = "false"

        from app.settings import get_settings
        get_settings.cache_clear()

        resp = client.post("/v1/x402/premium/fx-lookup", json={})
        accepts = resp.json()["accepts"]
        assert not any(a.get("payment_type") == "eip3009_facilitator" for a in accepts)

        os.environ["X402_ENABLE_FLARE_USDT0"] = "true"
        get_settings.cache_clear()


# ── USDT0 payment verification ────────────────────────────────────────────────

class TestUSDT0Payment:

    def _payment_header(self, settlement_tx=SETTLEMENT_TX):
        return json.dumps({
            "chain": "flare",
            "chain_id": 14,
            "currency": "USDT0",
            "payment_type": "eip3009_facilitator",
            "token": USDT0,
            "facilitator": FACILITATOR,
            "recipient": RECIPIENT,
            "amount": "0.001",
            "settlement_tx_hash": settlement_tx,
        })

    def test_valid_usdt0_payment_unlocks_endpoint(self, client):
        with patch("app.x402_flare.FlarePaymentVerifier") as MockVerifier:
            mock_instance = AsyncMock()
            mock_instance.verify_usdt0_settlement_tx.return_value = (True, "0xpaymentid", None)
            MockVerifier.return_value = mock_instance

            with patch("app.x402._check_tx_not_replayed", new_callable=AsyncMock):
                with patch("app.x402._record_usdt0_payment", new_callable=AsyncMock):
                    resp = client.post(
                        "/v1/x402/premium/fx-lookup",
                        json={"base_ccy": "USD"},
                        headers={"X-PAYMENT": self._payment_header()},
                    )
        assert resp.status_code == 200

    def test_invalid_settlement_tx_is_rejected(self, client):
        with patch("app.x402_flare.FlarePaymentVerifier") as MockVerifier:
            mock_instance = AsyncMock()
            mock_instance.verify_usdt0_settlement_tx.return_value = (False, None, "transaction_not_found")
            MockVerifier.return_value = mock_instance

            resp = client.post(
                "/v1/x402/premium/fx-lookup",
                json={},
                headers={"X-PAYMENT": self._payment_header()},
            )
        assert resp.status_code == 403
        assert "transaction_not_found" in resp.json()["detail"]

    def test_wrong_token_address_is_rejected(self, client):
        header = json.dumps({
            "chain": "flare", "chain_id": 14, "currency": "USDT0",
            "payment_type": "eip3009_facilitator",
            "token": "0x" + "00" * 20,  # wrong token
            "facilitator": FACILITATOR,
            "settlement_tx_hash": SETTLEMENT_TX,
        })
        resp = client.post(
            "/v1/x402/premium/fx-lookup",
            json={},
            headers={"X-PAYMENT": header},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "wrong_token_address"

    def test_wrong_facilitator_address_is_rejected(self, client):
        header = json.dumps({
            "chain": "flare", "chain_id": 14, "currency": "USDT0",
            "payment_type": "eip3009_facilitator",
            "token": USDT0,
            "facilitator": "0x" + "00" * 20,  # wrong facilitator
            "settlement_tx_hash": SETTLEMENT_TX,
        })
        resp = client.post(
            "/v1/x402/premium/fx-lookup",
            json={},
            headers={"X-PAYMENT": header},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "wrong_facilitator_address"

    def test_replayed_settlement_tx_is_rejected(self, client):
        with patch("app.x402._check_tx_not_replayed") as mock_check:
            from fastapi import HTTPException
            mock_check.side_effect = HTTPException(status_code=409, detail="payment_already_used")

            with patch("app.x402_flare.FlarePaymentVerifier") as MockVerifier:
                mock_instance = AsyncMock()
                mock_instance.verify_usdt0_settlement_tx.return_value = (True, "0xid", None)
                MockVerifier.return_value = mock_instance

                resp = client.post(
                    "/v1/x402/premium/fx-lookup",
                    json={},
                    headers={"X-PAYMENT": self._payment_header()},
                )
        assert resp.status_code == 409
        assert resp.json()["detail"] == "payment_already_used"

    def test_malformed_payment_header_returns_400(self, client):
        resp = client.post(
            "/v1/x402/premium/fx-lookup",
            json={},
            headers={"X-PAYMENT": "not valid json"},
        )
        assert resp.status_code == 400


# ── Native FLR payment ────────────────────────────────────────────────────────

class TestFLRPayment:

    def _flr_header(self, tx=FLR_TX):
        return json.dumps({
            "chain": "flare", "chain_id": 14,
            "currency": "FLR", "payment_type": "native_transfer",
            "tx_hash": tx, "from": PAYER, "to": RECIPIENT, "amount": "0.05",
        })

    def test_valid_flr_payment_unlocks_endpoint(self, client):
        with patch("app.x402_flare.FlarePaymentVerifier") as MockVerifier:
            mock_instance = AsyncMock()
            mock_instance.verify_flr_transfer.return_value = (True, None)
            MockVerifier.return_value = mock_instance

            with patch("app.x402._check_tx_not_replayed", new_callable=AsyncMock):
                with patch("app.x402._record_flr_payment", new_callable=AsyncMock):
                    resp = client.post(
                        "/v1/x402/premium/fx-lookup",
                        json={"base_ccy": "USD"},
                        headers={"X-PAYMENT": self._flr_header()},
                    )
        assert resp.status_code == 200

    def test_invalid_flr_transfer_is_rejected(self, client):
        with patch("app.x402_flare.FlarePaymentVerifier") as MockVerifier:
            mock_instance = AsyncMock()
            mock_instance.verify_flr_transfer.return_value = (False, "wrong_recipient")
            MockVerifier.return_value = mock_instance

            resp = client.post(
                "/v1/x402/premium/fx-lookup",
                json={},
                headers={"X-PAYMENT": self._flr_header()},
            )
        assert resp.status_code == 403


# ── Existing endpoints still work ────────────────────────────────────────────

class TestExistingEndpointsPreserved:

    def test_health_still_works(self, client):
        resp = client.get("/v1/health")
        assert resp.status_code == 200

    def test_pricing_endpoint_still_works(self, client):
        resp = client.get("/v1/x402/pricing")
        assert resp.status_code == 200

    def test_openapi_docs_include_premium_endpoints(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/v1/x402/premium/fx-lookup" in paths
        assert "/v1/x402/premium/verify-bundle" in paths
