"""Unit tests for USDT0 EIP-3009 x402 payment support.

Tests are isolated (no live RPC calls). FlarePaymentVerifier is mocked
where network access would otherwise be required.
"""
from __future__ import annotations

import json
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.x402_flare import (
    parse_flare_payment,
    FlareUSDT0Payment,
    FlareNativePayment,
    usdt0_to_raw,
    flr_to_wei,
    build_402_payment_options,
    FlarePaymentVerifier,
)


# ── Constants ─────────────────────────────────────────────────────────────────

USDT0 = "0xe7cd86e13AC4309349F30B3435a9d337750fC82D"
FACILITATOR = "0xFacilitatorAddress0000000000000000000000"
RECIPIENT = "0xRecipientAddress00000000000000000000000"
PAYER = "0xPayerAddress000000000000000000000000000"
NONCE = "0x" + "ab" * 32
SETTLEMENT_TX = "0x" + "cd" * 32


# ── Parser tests ──────────────────────────────────────────────────────────────

class TestParseFlarePayment:

    def _make_usdt0_header(self, **overrides) -> str:
        base = {
            "chain": "flare",
            "chain_id": 14,
            "currency": "USDT0",
            "payment_type": "eip3009_facilitator",
            "token": USDT0,
            "facilitator": FACILITATOR,
            "from": PAYER,
            "to": RECIPIENT,
            "value": "1000",
            "valid_after": "0",
            "valid_before": "9999999999",
            "nonce": NONCE,
            "v": 27,
            "r": "0x" + "aa" * 32,
            "s": "0x" + "bb" * 32,
            "authorization_type": "receiveWithAuthorization",
        }
        base.update(overrides)
        return json.dumps(base)

    def test_parse_usdt0_authorization(self):
        header = self._make_usdt0_header()
        result = parse_flare_payment(header)
        assert isinstance(result, FlareUSDT0Payment)
        assert result.payment_type == "eip3009_facilitator"
        assert result.currency == "USDT0"
        assert result.chain_id == 14
        assert result.nonce == NONCE
        assert result.authorization_type == "receiveWithAuthorization"

    def test_parse_usdt0_settlement_tx_mode(self):
        header = json.dumps({
            "chain": "flare",
            "chain_id": 14,
            "currency": "USDT0",
            "payment_type": "eip3009_facilitator",
            "token": USDT0,
            "facilitator": FACILITATOR,
            "recipient": RECIPIENT,
            "amount": "0.001",
            "settlement_tx_hash": SETTLEMENT_TX,
        })
        result = parse_flare_payment(header)
        assert isinstance(result, FlareUSDT0Payment)
        assert result.settlement_tx_hash == SETTLEMENT_TX
        assert result.from_address is None  # not provided in settlement-only mode

    def test_parse_native_flr(self):
        header = json.dumps({
            "chain": "flare",
            "chain_id": 14,
            "currency": "FLR",
            "payment_type": "native_transfer",
            "tx_hash": SETTLEMENT_TX,
            "from": PAYER,
            "to": RECIPIENT,
            "amount": "0.05",
        })
        result = parse_flare_payment(header)
        assert isinstance(result, FlareNativePayment)
        assert result.tx_hash == SETTLEMENT_TX
        assert result.currency == "FLR"

    def test_reject_wrong_chain(self):
        header = json.dumps({
            "chain": "ethereum",
            "chain_id": 1,
            "currency": "USDT0",
            "payment_type": "eip3009_facilitator",
            "token": USDT0,
            "facilitator": FACILITATOR,
        })
        result = parse_flare_payment(header)
        assert result is None

    def test_reject_invalid_json(self):
        result = parse_flare_payment("not json")
        assert result is None

    def test_reject_unknown_payment_type(self):
        header = json.dumps({
            "chain": "flare",
            "chain_id": 14,
            "currency": "USDC",
            "payment_type": "permit2",
        })
        result = parse_flare_payment(header)
        assert result is None


# ── Amount conversion ─────────────────────────────────────────────────────────

class TestAmountConversions:

    def test_usdt0_to_raw_001(self):
        assert usdt0_to_raw("0.001") == 1000

    def test_usdt0_to_raw_1(self):
        assert usdt0_to_raw("1.0") == 1_000_000

    def test_usdt0_to_raw_precise(self):
        assert usdt0_to_raw("0.000001") == 1

    def test_usdt0_to_raw_invalid(self):
        with pytest.raises(ValueError):
            usdt0_to_raw("not_a_number")

    def test_flr_to_wei_05(self):
        assert flr_to_wei("0.05") == 50_000_000_000_000_000

    def test_flr_to_wei_1(self):
        assert flr_to_wei("1") == 10 ** 18

    def test_flr_to_wei_invalid(self):
        with pytest.raises(ValueError):
            flr_to_wei("abc")


# ── 402 response builder ──────────────────────────────────────────────────────

class TestBuild402PaymentOptions:

    def _base_kwargs(self, **overrides):
        defaults = dict(
            usdc_enabled=True,
            usdt0_enabled=True,
            flr_enabled=True,
            usdc_recipient=RECIPIENT,
            usdt0_recipient=RECIPIENT,
            flr_recipient=RECIPIENT,
            usdc_amount="0.001",
            usdt0_amount="0.001",
            flr_amount="0.05",
            usdc_token="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            usdt0_token=USDT0,
            facilitator=FACILITATOR,
        )
        defaults.update(overrides)
        return defaults

    def test_all_enabled_returns_three_options(self):
        opts = build_402_payment_options(**self._base_kwargs())
        assert len(opts) == 3
        types = {o["payment_type"] for o in opts}
        assert types == {"erc20_transfer", "eip3009_facilitator", "native_transfer"}

    def test_usdt0_option_has_correct_fields(self):
        opts = build_402_payment_options(**self._base_kwargs())
        usdt0_opt = next(o for o in opts if o["payment_type"] == "eip3009_facilitator")
        assert usdt0_opt["token"] == USDT0
        assert usdt0_opt["facilitator"] == FACILITATOR
        assert usdt0_opt["chain_id"] == 14
        assert usdt0_opt["decimals"] == 6
        assert usdt0_opt["network"] == "flare"
        assert usdt0_opt["asset"] == "USDT0"

    def test_disable_usdt0(self):
        opts = build_402_payment_options(**self._base_kwargs(usdt0_enabled=False))
        types = [o["payment_type"] for o in opts]
        assert "eip3009_facilitator" not in types
        assert len(opts) == 2

    def test_disable_flr(self):
        opts = build_402_payment_options(**self._base_kwargs(flr_enabled=False))
        types = [o["payment_type"] for o in opts]
        assert "native_transfer" not in types

    def test_usdt0_hidden_when_facilitator_missing(self):
        opts = build_402_payment_options(**self._base_kwargs(facilitator=None))
        types = [o["payment_type"] for o in opts]
        assert "eip3009_facilitator" not in types

    def test_usdt0_hidden_when_recipient_missing(self):
        opts = build_402_payment_options(**self._base_kwargs(usdt0_recipient=None))
        types = [o["payment_type"] for o in opts]
        assert "eip3009_facilitator" not in types

    def test_all_disabled_returns_empty(self):
        opts = build_402_payment_options(
            **self._base_kwargs(
                usdc_enabled=False,
                usdt0_enabled=False,
                flr_enabled=False,
            )
        )
        assert opts == []


# ── Settlement TX verification (mocked) ──────────────────────────────────────

class TestVerifyUSDT0SettlementTx:
    """Test verify_usdt0_settlement_tx with mocked Web3."""

    def _make_payment(self, **kwargs) -> FlareUSDT0Payment:
        defaults = dict(
            chain="flare",
            chain_id=14,
            currency="USDT0",
            payment_type="eip3009_facilitator",
            token=USDT0,
            facilitator=FACILITATOR,
            settlement_tx_hash=SETTLEMENT_TX,
            recipient=RECIPIENT,
            amount="0.001",
        )
        defaults.update(kwargs)
        return FlareUSDT0Payment(**defaults)

    def _mock_receipt(self, status=1, logs=None, block=100, tx_to=FACILITATOR):
        receipt = MagicMock()
        receipt.__getitem__ = lambda self, key: {
            "status": status,
            "blockNumber": block,
            "to": tx_to,
            "logs": logs or [],
        }[key]
        receipt.get = lambda key, default=None: {
            "status": status,
            "blockNumber": block,
            "to": tx_to,
            "logs": logs or [],
        }.get(key, default)
        return receipt

    @pytest.mark.asyncio
    async def test_reject_missing_settlement_hash(self):
        verifier = FlarePaymentVerifier.__new__(FlarePaymentVerifier)
        payment = FlareUSDT0Payment(
            chain="flare", chain_id=14, currency="USDT0",
            payment_type="eip3009_facilitator", token=USDT0, facilitator=FACILITATOR,
        )
        ok, _, err = await verifier.verify_usdt0_settlement_tx(
            payment, USDT0, RECIPIENT, 1000, FACILITATOR
        )
        assert not ok
        assert err == "missing_settlement_tx_hash"

    @pytest.mark.asyncio
    async def test_reject_reverted_tx(self):
        verifier = FlarePaymentVerifier.__new__(FlarePaymentVerifier)
        verifier.w3 = MagicMock()
        verifier.w3.eth.get_transaction_receipt.return_value = self._mock_receipt(status=0)
        verifier.w3.eth.block_number = 101

        ok, _, err = await verifier.verify_usdt0_settlement_tx(
            self._make_payment(), USDT0, RECIPIENT, 1000, FACILITATOR
        )
        assert not ok
        assert err == "transaction_reverted"

    @pytest.mark.asyncio
    async def test_reject_wrong_facilitator(self):
        verifier = FlarePaymentVerifier.__new__(FlarePaymentVerifier)
        verifier.w3 = MagicMock()
        verifier.w3.eth.get_transaction_receipt.return_value = self._mock_receipt(
            tx_to="0xWrongFacilitator"
        )
        verifier.w3.eth.block_number = 101

        ok, _, err = await verifier.verify_usdt0_settlement_tx(
            self._make_payment(), USDT0, RECIPIENT, 1000, FACILITATOR
        )
        assert not ok
        assert err == "wrong_facilitator"

    @pytest.mark.asyncio
    async def test_reject_no_event_logs(self):
        verifier = FlarePaymentVerifier.__new__(FlarePaymentVerifier)
        verifier.w3 = MagicMock()
        verifier.w3.eth.get_transaction_receipt.return_value = self._mock_receipt(logs=[])
        verifier.w3.eth.block_number = 101

        ok, _, err = await verifier.verify_usdt0_settlement_tx(
            self._make_payment(), USDT0, RECIPIENT, 1000, FACILITATOR
        )
        assert not ok
        assert err == "facilitator_event_not_found"


# ── Native FLR verification (mocked) ─────────────────────────────────────────

class TestVerifyFLRTransfer:

    @pytest.mark.asyncio
    async def test_reject_missing_tx_hash(self):
        verifier = FlarePaymentVerifier.__new__(FlarePaymentVerifier)
        payment = FlareNativePayment(tx_hash="")
        ok, err = await verifier.verify_flr_transfer(payment, RECIPIENT, 10**16)
        assert not ok
        assert err == "missing_tx_hash"

    @pytest.mark.asyncio
    async def test_reject_wrong_recipient(self):
        verifier = FlarePaymentVerifier.__new__(FlarePaymentVerifier)
        verifier.w3 = MagicMock()
        verifier.w3.eth.get_transaction.return_value = {
            "to": "0xWrongRecipient",
            "value": 10**18,
        }

        payment = FlareNativePayment(tx_hash=SETTLEMENT_TX)
        ok, err = await verifier.verify_flr_transfer(payment, RECIPIENT, 10**16)
        assert not ok
        assert err == "wrong_recipient"

    @pytest.mark.asyncio
    async def test_reject_insufficient_amount(self):
        verifier = FlarePaymentVerifier.__new__(FlarePaymentVerifier)
        verifier.w3 = MagicMock()
        verifier.w3.eth.get_transaction.return_value = {
            "to": RECIPIENT,
            "value": 1000,  # far below expected
        }

        payment = FlareNativePayment(tx_hash=SETTLEMENT_TX)
        ok, err = await verifier.verify_flr_transfer(payment, RECIPIENT, flr_to_wei("0.05"))
        assert not ok
        assert err == "insufficient_amount"
