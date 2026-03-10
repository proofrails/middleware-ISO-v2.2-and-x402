"""
Comprehensive smoke tests for x402 implementation.

Tests both new x402 functionality and verifies all pre-existing endpoints still work.
"""
import pytest
import requests
from typing import Dict, Any

# Configure base URL
BASE_URL = "http://127.0.0.1:8000"


class TestPreExistingEndpoints:
    """Verify all pre-existing endpoints still work correctly."""
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = requests.get(f"{BASE_URL}/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_list_receipts(self):
        """Test listing receipts endpoint."""
        response = requests.get(f"{BASE_URL}/v1/receipts")
        assert response.status_code in [200, 401]  # May require auth
    
    def test_get_config(self):
        """Test get configuration endpoint."""
        response = requests.get(f"{BASE_URL}/v1/config")
        assert response.status_code == 200
    
    def test_verify_endpoint_exists(self):
        """Test verify bundle endpoint exists."""
        # POST without data should return 422 (validation error) not 404
        response = requests.post(f"{BASE_URL}/v1/iso/verify")
        assert response.status_code in [422, 400]  # Not 404
    
    def test_refund_endpoint_exists(self):
        """Test refund endpoint exists."""
        response = requests.post(f"{BASE_URL}/v1/iso/refund")
        assert response.status_code in [422, 400, 401]  # Not 404


class TestX402ConfigurationEndpoints:
    """Test x402 configuration and analytics endpoints."""
    
    def test_get_pricing(self):
        """Test GET /v1/x402/pricing endpoint."""
        response = requests.get(f"{BASE_URL}/v1/x402/pricing")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_payments(self):
        """Test GET /v1/x402/payments endpoint."""
        response = requests.get(f"{BASE_URL}/v1/x402/payments")
        # May require auth, but endpoint should exist
        assert response.status_code in [200, 401]
    
    def test_get_revenue(self):
        """Test GET /v1/x402/revenue endpoint."""
        response = requests.get(f"{BASE_URL}/v1/x402/revenue?days=7")
        # May require admin auth
        assert response.status_code in [200, 403, 401]
    
    def test_verify_payment_endpoint_exists(self):
        """Test POST /v1/x402/verify-payment endpoint exists."""
        response = requests.post(f"{BASE_URL}/v1/x402/verify-payment")
        # Should return validation error, not 404
        assert response.status_code in [422, 400]


class TestX402PremiumEndpoints:
    """Test x402 premium (payment-gated) endpoints."""
    
    def test_premium_verify_bundle_exists(self):
        """Test premium verify bundle endpoint exists."""
        response = requests.post(f"{BASE_URL}/v1/x402/premium/verify-bundle")
        # Should require payment (402) or validation error, not 404
        assert response.status_code in [402, 422, 400]
    
    def test_premium_generate_statement_exists(self):
        """Test premium generate statement endpoint exists."""
        response = requests.post(f"{BASE_URL}/v1/x402/premium/generate-statement")
        assert response.status_code in [402, 422, 400]
    
    def test_premium_fx_lookup_exists(self):
        """Test premium FX lookup endpoint exists."""
        response = requests.post(f"{BASE_URL}/v1/x402/premium/fx-lookup")
        assert response.status_code in [402, 422, 400]
    
    def test_premium_bulk_verify_exists(self):
        """Test premium bulk verify endpoint exists."""
        response = requests.post(f"{BASE_URL}/v1/x402/premium/bulk-verify")
        assert response.status_code in [402, 422, 400]
    
    def test_premium_refund_exists(self):
        """Test premium refund endpoint exists."""
        response = requests.post(f"{BASE_URL}/v1/x402/premium/refund")
        assert response.status_code in [402, 422, 400]


class TestAgentManagementEndpoints:
    """Test agent management CRUD endpoints."""
    
    def test_list_agents(self):
        """Test GET /v1/agents endpoint."""
        response = requests.get(f"{BASE_URL}/v1/agents")
        # May require auth
        assert response.status_code in [200, 401]
    
    def test_create_agent_endpoint_exists(self):
        """Test POST /v1/agents endpoint exists."""
        response = requests.post(f"{BASE_URL}/v1/agents")
        # Should require auth or validation error, not 404
        assert response.status_code in [422, 400, 401]


class TestAPIDocumentation:
    """Verify API documentation is accessible."""
    
    def test_openapi_docs(self):
        """Test OpenAPI docs endpoint."""
        response = requests.get(f"{BASE_URL}/docs")
        assert response.status_code == 200
    
    def test_openapi_json(self):
        """Test OpenAPI JSON endpoint."""
        response = requests.get(f"{BASE_URL}/openapi.json")
        assert response.status_code == 200
        data = response.json()
        
        # Verify x402 endpoints are documented
        assert "/v1/x402/pricing" in data["paths"]
        assert "/v1/agents" in data["paths"]


class TestIntegration:
    """Integration tests combining multiple features."""
    
    def test_create_receipt_workflow(self):
        """Test creating a receipt (pre-existing functionality)."""
        payload = {
            "tip_tx_hash": "0xtest123",
            "chain": "flare",
            "amount": "1.0",
            "currency": "FLR",
            "sender_wallet": "0xSender",
            "receiver_wallet": "0xReceiver",
            "reference": "smoke-test-001"
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/iso/record-tip",
            json=payload
        )
        
        # May require auth, but endpoint should work
        assert response.status_code in [200, 201, 401, 422]
        
        # If successful, verify we can list receipts
        if response.status_code in [200, 201]:
            list_response = requests.get(f"{BASE_URL}/v1/receipts")
            assert list_response.status_code in [200, 401]


def test_all_routes_registered():
    """Verify all expected routes are registered in the API."""
    response = requests.get(f"{BASE_URL}/openapi.json")
    assert response.status_code == 200
    data = response.json()
    
    # Pre-existing routes
    expected_existing = [
        "/v1/health",
        "/v1/receipts",
        "/v1/iso/record-tip",
        "/v1/iso/verify",
        "/v1/config",
    ]
    
    # New x402 routes
    expected_x402 = [
        "/v1/x402/pricing",
        "/v1/x402/payments",
        "/v1/x402/revenue",
        "/v1/x402/verify-payment",
        "/v1/x402/premium/verify-bundle",
        "/v1/x402/premium/generate-statement",
        "/v1/x402/premium/fx-lookup",
        "/v1/x402/premium/bulk-verify",
        "/v1/x402/premium/refund",
        "/v1/agents",
    ]
    
    all_expected = expected_existing + expected_x402
    paths = data["paths"]
    
    missing_routes = [route for route in all_expected if route not in paths]
    assert not missing_routes, f"Missing routes: {missing_routes}"


def test_no_breaking_changes():
    """Verify no breaking changes in existing endpoints."""
    # Test that old endpoints still return expected structure
    
    # Health endpoint
    response = requests.get(f"{BASE_URL}/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    
    # Config endpoint
    response = requests.get(f"{BASE_URL}/v1/config")
    assert response.status_code == 200
    data = response.json()
    # Config should have expected structure (organization, ledger, etc.)
    assert isinstance(data, dict)


if __name__ == "__main__":
    print("Running x402 smoke tests...")
    print("=" * 60)
    
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
