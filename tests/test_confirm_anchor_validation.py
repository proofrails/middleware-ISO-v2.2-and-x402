from __future__ import annotations

from datetime import datetime, timezone

import pytest


def test_verify_anchor_tx_parses_log(monkeypatch):
    """Unit-test the log decoding logic without any live RPC."""

    from app.anchor import EVIDENCE_ANCHORED_TOPIC0, verify_anchor_tx

    expected_hash = "0x" + "11" * 32
    txid = "0x" + "aa" * 32
    contract_addr = "0x" + "22" * 20

    # ABI encoding for (bytes32 bundleHash, uint256 ts):
    # data = bundleHash (32) + ts (32)
    ts = 123
    data_hex = "0x" + expected_hash[2:] + (ts).to_bytes(32, "big").hex()

    class DummyEth:
        def get_transaction_receipt(self, _txid):
            assert _txid == txid
            return {
                "status": 1,
                "blockNumber": 10,
                "logs": [
                    {
                        "address": contract_addr,
                        "topics": [EVIDENCE_ANCHORED_TOPIC0],
                        "data": data_hex,
                    }
                ],
            }

        def get_block(self, block_number):
            assert block_number == 10
            return {"timestamp": 1000}

    class DummyW3:
        def __init__(self):
            self.eth = DummyEth()

    import app.anchor as anchor_mod

    monkeypatch.setattr(anchor_mod, "_load_web3", lambda _rpc_url: DummyW3())

    ok, blk, anchored_at = verify_anchor_tx(
        txid=txid,
        expected_bundle_hash_hex=expected_hash,
        rpc_url="http://example",
        contract_addr=contract_addr,
    )

    assert ok is True
    assert blk == 10
    assert anchored_at == datetime.fromtimestamp(1000, tz=timezone.utc)


def test_verify_anchor_tx_rejects_wrong_hash(monkeypatch):
    from app.anchor import EVIDENCE_ANCHORED_TOPIC0, verify_anchor_tx

    expected_hash = "0x" + "11" * 32
    wrong_hash = "0x" + "33" * 32
    txid = "0x" + "aa" * 32
    contract_addr = "0x" + "22" * 20

    data_hex = "0x" + wrong_hash[2:] + (1).to_bytes(32, "big").hex()

    class DummyEth:
        def get_transaction_receipt(self, _txid):
            return {
                "status": 1,
                "blockNumber": 10,
                "logs": [
                    {
                        "address": contract_addr,
                        "topics": [EVIDENCE_ANCHORED_TOPIC0],
                        "data": data_hex,
                    }
                ],
            }

        def get_block(self, _block_number):
            return {"timestamp": 1000}

    class DummyW3:
        def __init__(self):
            self.eth = DummyEth()

    import app.anchor as anchor_mod

    monkeypatch.setattr(anchor_mod, "_load_web3", lambda _rpc_url: DummyW3())

    ok, blk, anchored_at = verify_anchor_tx(
        txid=txid,
        expected_bundle_hash_hex=expected_hash,
        rpc_url="http://example",
        contract_addr=contract_addr,
    )

    assert ok is False
    assert blk == 10
    assert anchored_at is None
