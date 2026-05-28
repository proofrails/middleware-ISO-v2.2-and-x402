"""Agent anchoring feature tests — in-process, no external server required."""
from __future__ import annotations

import hashlib
import json
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def agent(client, admin_headers):
    """Create a test agent and clean up after the test."""
    resp = client.post(
        "/v1/agents",
        json={
            "name": "Anchoring Test Agent",
            "wallet_address": "0x1234567890123456789012345678901234567890",
        },
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201), resp.text
    data = resp.json()
    yield data
    client.delete(f"/v1/agents/{data['id']}", headers=admin_headers)


# ── Config endpoints ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_get_default_anchoring_config(client, agent, admin_headers):
    resp = client.get(f"/v1/agents/{agent['id']}/anchoring-config", headers=admin_headers)
    assert resp.status_code == 200
    cfg = resp.json()
    assert cfg["auto_anchor_enabled"] is False
    assert cfg["anchor_on_payment"] is False
    assert cfg["anchor_wallet"] is None


@pytest.mark.unit
def test_update_anchoring_config(client, agent, admin_headers):
    resp = client.put(
        f"/v1/agents/{agent['id']}/anchoring-config",
        json={
            "auto_anchor_enabled": True,
            "anchor_on_payment": True,
            "anchor_wallet_address": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    cfg = resp.json()
    assert cfg["auto_anchor_enabled"] is True
    assert cfg["anchor_on_payment"] is True
    assert cfg["anchor_wallet"] == "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"


@pytest.mark.unit
def test_update_then_get_config_roundtrip(client, agent, admin_headers):
    client.put(
        f"/v1/agents/{agent['id']}/anchoring-config",
        json={"auto_anchor_enabled": True, "anchor_on_payment": False},
        headers=admin_headers,
    )
    resp = client.get(f"/v1/agents/{agent['id']}/anchoring-config", headers=admin_headers)
    assert resp.status_code == 200
    cfg = resp.json()
    assert cfg["auto_anchor_enabled"] is True
    assert cfg["anchor_on_payment"] is False


@pytest.mark.unit
def test_disable_anchoring(client, agent, admin_headers):
    # Enable first
    client.put(
        f"/v1/agents/{agent['id']}/anchoring-config",
        json={"auto_anchor_enabled": True, "anchor_on_payment": True},
        headers=admin_headers,
    )
    # Disable
    resp = client.put(
        f"/v1/agents/{agent['id']}/anchoring-config",
        json={"auto_anchor_enabled": False, "anchor_on_payment": False},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    cfg = resp.json()
    assert cfg["auto_anchor_enabled"] is False
    assert cfg["anchor_on_payment"] is False


# ── anchor-data endpoint ──────────────────────────────────────────────────────

@pytest.mark.unit
def test_anchor_data_basic(client, agent, admin_headers):
    resp = client.post(
        f"/v1/agents/{agent['id']}/anchor-data",
        json={
            "data": {"payment_id": "pay-001", "amount": 100.50, "currency": "USD"},
            "description": "Test anchor",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "id" in body
    assert "anchor_hash" in body
    assert body["anchor_hash"].startswith("0x")
    assert len(body["anchor_hash"]) == 66  # 0x + 64 hex chars
    assert body["status"] == "pending"
    assert body["agent_id"] == agent["id"]


@pytest.mark.unit
def test_anchor_data_hash_is_deterministic(client, agent, admin_headers):
    """Same data must always produce the same hash."""
    data = {"key": "value", "nested": {"a": 1}}

    resp1 = client.post(
        f"/v1/agents/{agent['id']}/anchor-data",
        json={"data": data},
        headers=admin_headers,
    )
    resp2 = client.post(
        f"/v1/agents/{agent['id']}/anchor-data",
        json={"data": data},
        headers=admin_headers,
    )
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["anchor_hash"] == resp2.json()["anchor_hash"]


@pytest.mark.unit
def test_anchor_data_hash_matches_canonical_json(client, agent, admin_headers):
    """Verify the hash algorithm: SHA-256 of sorted-keys compact JSON."""
    data = {"z": 2, "a": 1}
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    expected_hash = "0x" + hashlib.sha256(canonical.encode()).hexdigest()

    resp = client.post(
        f"/v1/agents/{agent['id']}/anchor-data",
        json={"data": data},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["anchor_hash"] == expected_hash


@pytest.mark.unit
def test_anchor_data_missing_data_field(client, agent, admin_headers):
    resp = client.post(
        f"/v1/agents/{agent['id']}/anchor-data",
        json={"description": "missing data field"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


@pytest.mark.unit
def test_anchor_data_submit_onchain_false(client, agent, admin_headers):
    """submit_onchain=false (default) should return pending without dispatching a job."""
    resp = client.post(
        f"/v1/agents/{agent['id']}/anchor-data",
        json={"data": {"test": "no-chain"}, "submit_onchain": False},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["submit_onchain"] is False
    assert body["status"] == "pending"


@pytest.mark.unit
def test_anchor_complex_nested_data(client, agent, admin_headers):
    data = {
        "payment": {
            "id": "pay-123",
            "amount": 1000.00,
            "currency": "EUR",
            "debtor": {"name": "Alice", "account": "DE89370400440532013000"},
            "creditor": {"name": "Bob", "account": "GB82WEST12345698765432"},
        },
        "metadata": {"reference": "REF-2026-001"},
    }
    resp = client.post(
        f"/v1/agents/{agent['id']}/anchor-data",
        json={"data": data, "description": "Complex payment"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["anchor_hash"].startswith("0x")
    assert len(body["anchor_hash"]) == 66


# ── List anchors ──────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_list_anchors_empty(client, agent, admin_headers):
    resp = client.get(f"/v1/agents/{agent['id']}/anchors", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.unit
def test_list_anchors_after_creating(client, agent, admin_headers):
    for i in range(3):
        client.post(
            f"/v1/agents/{agent['id']}/anchor-data",
            json={"data": {"index": i}},
            headers=admin_headers,
        )

    resp = client.get(f"/v1/agents/{agent['id']}/anchors", headers=admin_headers)
    assert resp.status_code == 200
    anchors = resp.json()
    assert len(anchors) >= 3
    for a in anchors:
        assert "id" in a
        assert "bundle_hash" in a
        assert "status" in a
        assert "chain" in a


# ── Error cases ───────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_invalid_agent_id_returns_404(client, admin_headers):
    resp = client.get("/v1/agents/nonexistent-agent-id/anchors", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.unit
def test_anchoring_config_requires_auth(client, agent):
    resp = client.get(f"/v1/agents/{agent['id']}/anchoring-config")
    assert resp.status_code == 401


@pytest.mark.unit
def test_anchor_data_requires_auth(client, agent):
    resp = client.post(
        f"/v1/agents/{agent['id']}/anchor-data",
        json={"data": {"test": "value"}},
    )
    assert resp.status_code == 401
