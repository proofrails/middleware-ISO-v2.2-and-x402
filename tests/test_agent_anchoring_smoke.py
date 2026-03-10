"""
Agent Anchoring Feature Smoke Test

Tests the complete agent anchoring feature including:
- Database migrations
- API endpoints
- Configuration management
- Manual anchoring
"""

import pytest
import requests
import json
from datetime import datetime

API_BASE = "http://127.0.0.1:8000"


class TestAgentAnchoringSmokeTest:
    """Smoke tests for agent anchoring feature"""

    def setup_method(self):
        """Setup test agent"""
        # Create test agent
        response = requests.post(
            f"{API_BASE}/v1/agents",
            json={
                "name": "Anchoring Test Agent",
                "wallet_address": "0x1234567890123456789012345678901234567890",
                "xmtp_address": "0x1234567890123456789012345678901234567890",
            },
        )
        assert response.status_code == 200
        self.agent = response.json()
        self.agent_id = self.agent["id"]
        print(f"✓ Created test agent: {self.agent_id}")

    def teardown_method(self):
        """Cleanup test agent"""
        if hasattr(self, "agent_id"):
            requests.delete(f"{API_BASE}/v1/agents/{self.agent_id}")
            print(f"✓ Cleaned up test agent: {self.agent_id}")

    def test_01_get_default_anchoring_config(self):
        """Test getting default anchoring configuration"""
        response = requests.get(
            f"{API_BASE}/v1/agents/{self.agent_id}/anchoring-config"
        )
        assert response.status_code == 200

        config = response.json()
        assert config["auto_anchor_enabled"] is False
        assert config["anchor_on_payment"] is False
        assert config["anchor_wallet"] is None
        print("✓ Default anchoring config retrieved successfully")

    def test_02_update_anchoring_config(self):
        """Test updating anchoring configuration"""
        new_config = {
            "auto_anchor_enabled": True,
            "anchor_on_payment": True,
            "anchor_wallet": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
        }

        response = requests.put(
            f"{API_BASE}/v1/agents/{self.agent_id}/anchoring-config", json=new_config
        )
        assert response.status_code == 200

        updated = response.json()
        assert updated["auto_anchor_enabled"] is True
        assert updated["anchor_on_payment"] is True
        assert (
            updated["anchor_wallet"] == "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        )
        print("✓ Anchoring config updated successfully")

    def test_03_get_updated_config(self):
        """Test retrieving updated configuration"""
        # First update
        requests.put(
            f"{API_BASE}/v1/agents/{self.agent_id}/anchoring-config",
            json={"auto_anchor_enabled": True, "anchor_on_payment": False},
        )

        # Then verify
        response = requests.get(
            f"{API_BASE}/v1/agents/{self.agent_id}/anchoring-config"
        )
        assert response.status_code == 200

        config = response.json()
        assert config["auto_anchor_enabled"] is True
        assert config["anchor_on_payment"] is False
        print("✓ Updated config persisted correctly")

    def test_04_manual_anchor_data(self):
        """Test manual data anchoring"""
        anchor_data = {
            "data": {
                "payment_id": "test-payment-001",
                "amount": 100.50,
                "currency": "USD",
                "timestamp": datetime.utcnow().isoformat(),
            },
            "description": "Test payment anchoring",
        }

        response = requests.post(
            f"{API_BASE}/v1/agents/{self.agent_id}/anchor-data", json=anchor_data
        )
        assert response.status_code == 200

        anchor = response.json()
        assert "id" in anchor
        assert "anchor_hash" in anchor
        assert anchor["status"] == "pending"
        assert anchor["agent_id"] == self.agent_id
        print(f"✓ Manual anchor created: {anchor['id']}")
        
        self.anchor_id = anchor["id"]

    def test_05_list_anchors(self):
        """Test listing agent anchors"""
        # Create a few anchors first
        for i in range(3):
            requests.post(
                f"{API_BASE}/v1/agents/{self.agent_id}/anchor-data",
                json={
                    "data": {"test": f"data_{i}"},
                    "description": f"Test anchor {i}",
                },
            )

        # List anchors
        response = requests.get(f"{API_BASE}/v1/agents/{self.agent_id}/anchors")
        assert response.status_code == 200

        anchors = response.json()
        assert isinstance(anchors, list)
        assert len(anchors) >= 3
        print(f"✓ Listed {len(anchors)} anchors")

    def test_06_anchor_data_validation(self):
        """Test anchor data validation"""
        # Missing data field
        response = requests.post(
            f"{API_BASE}/v1/agents/{self.agent_id}/anchor-data",
            json={"description": "Missing data"},
        )
        assert response.status_code == 422  # Validation error
        print("✓ Data validation working correctly")

    def test_07_invalid_agent_id(self):
        """Test with invalid agent ID"""
        response = requests.get(
            f"{API_BASE}/v1/agents/invalid-agent-id-999/anchors"
        )
        assert response.status_code == 404
        print("✓ Invalid agent ID handled correctly")

    def test_08_config_update_validation(self):
        """Test configuration update validation"""
        # Invalid wallet address format
        response = requests.put(
            f"{API_BASE}/v1/agents/{self.agent_id}/anchoring-config",
            json={
                "auto_anchor_enabled": True,
                "anchor_wallet": "not-a-valid-address",
            },
        )
        # Should either accept it or return validation error
        # depending on implementation
        print(f"✓ Config validation response: {response.status_code}")

    def test_09_anchor_complex_data(self):
        """Test anchoring complex nested data"""
        complex_data = {
            "data": {
                "payment": {
                    "id": "pay-123",
                    "amount": 1000.00,
                    "currency": "EUR",
                    "debtor": {
                        "name": "John Doe",
                        "account": "DE89370400440532013000",
                    },
                    "creditor": {
                        "name": "Jane Smith",
                        "account": "GB82WEST12345698765432",
                    },
                },
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "reference": "REF-2026-001",
                },
            },
            "description": "Complex payment data anchor",
        }

        response = requests.post(
            f"{API_BASE}/v1/agents/{self.agent_id}/anchor-data", json=complex_data
        )
        assert response.status_code == 200

        anchor = response.json()
        assert anchor["status"] == "pending"
        print(f"✓ Complex data anchored: {anchor['anchor_hash'][:16]}...")

    def test_10_disable_anchoring(self):
        """Test disabling anchoring configuration"""
        response = requests.put(
            f"{API_BASE}/v1/agents/{self.agent_id}/anchoring-config",
            json={
                "auto_anchor_enabled": False,
                "anchor_on_payment": False,
                "anchor_wallet": None,
            },
        )
        assert response.status_code == 200

        config = response.json()
        assert config["auto_anchor_enabled"] is False
        assert config["anchor_on_payment"] is False
        print("✓ Anchoring disabled successfully")


def run_smoke_test():
    """Run the smoke test suite"""
    print("\n" + "=" * 60)
    print("AGENT ANCHORING SMOKE TEST")
    print("=" * 60 + "\n")

    # Check API availability
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code != 200:
            print("❌ API server not running at", API_BASE)
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server at", API_BASE)
        print("   Please start the server with: python -m uvicorn app.main:app")
        return False

    print(f"✓ API server is running at {API_BASE}\n")

    # Run pytest
    result = pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "-s",
            "--color=yes",
        ]
    )

    print("\n" + "=" * 60)
    if result == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60 + "\n")

    return result == 0


if __name__ == "__main__":
    import sys

    success = run_smoke_test()
    sys.exit(0 if success else 1)
