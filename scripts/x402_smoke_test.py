#!/usr/bin/env python3
"""
Quick smoke test for x402 implementation.
Verifies critical endpoints and backward compatibility.
"""
import sys
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(method, url, expected_codes, description):
    """Test an endpoint and return success status."""
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        else:
            response = requests.post(url, json={}, timeout=5)
        
        success = response.status_code in expected_codes
        status = "✅" if success else "❌"
        print(f"{status} {description}: {response.status_code}")
        return success
    except Exception as e:
        print(f"❌ {description}: ERROR - {str(e)}")
        return False

def main():
    print("=" * 70)
    print("🧪 x402 SMOKE TEST - Quick Verification")
    print("=" * 70)
    print()
    
    results = []
    
    # Pre-existing endpoints
    print("📋 Testing Pre-Existing Endpoints...")
    results.append(test_endpoint("GET", f"{BASE_URL}/v1/health", [200], "Health check"))
    results.append(test_endpoint("GET", f"{BASE_URL}/v1/receipts", [200, 401], "List receipts"))
    results.append(test_endpoint("GET", f"{BASE_URL}/v1/config", [200], "Get config"))
    results.append(test_endpoint("POST", f"{BASE_URL}/v1/iso/verify", [422, 400], "Verify endpoint"))
    print()
    
    # New x402 endpoints
    print("🤖 Testing x402 Configuration Endpoints...")
    results.append(test_endpoint("GET", f"{BASE_URL}/v1/x402/pricing", [200], "Get pricing"))
    results.append(test_endpoint("GET", f"{BASE_URL}/v1/x402/payments", [200, 401], "List payments"))
    results.append(test_endpoint("GET", f"{BASE_URL}/v1/x402/revenue?days=7", [200, 401, 403], "Revenue analytics"))
    print()
    
    # Premium endpoints
    print("💰 Testing x402 Premium Endpoints...")
    results.append(test_endpoint("POST", f"{BASE_URL}/v1/x402/premium/verify-bundle", [402, 422, 400], "Premium verify"))
    results.append(test_endpoint("POST", f"{BASE_URL}/v1/x402/premium/generate-statement", [402, 422, 400], "Premium statement"))
    print()
    
    # Agent endpoints
    print("🔧 Testing Agent Management Endpoints...")
    results.append(test_endpoint("GET", f"{BASE_URL}/v1/agents", [200, 401], "List agents"))
    results.append(test_endpoint("POST", f"{BASE_URL}/v1/agents", [422, 400, 401], "Create agent"))
    print()
    
    # API docs
    print("📚 Testing API Documentation...")
    results.append(test_endpoint("GET", f"{BASE_URL}/docs", [200], "OpenAPI docs"))
    results.append(test_endpoint("GET", f"{BASE_URL}/openapi.json", [200], "OpenAPI JSON"))
    print()
    
    # Summary
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print("=" * 70)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    print("=" * 70)
    
    if failed > 0:
        print(f"❌ {failed} test(s) failed")
        print("⚠️  Please check the API is running and all migrations are applied")
        return 1
    else:
        print("✅ All tests passed!")
        print("✅ x402 implementation verified")
        print("✅ No regressions detected")
        return 0

if __name__ == "__main__":
    sys.exit(main())
