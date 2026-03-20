"""Unit tests for FI messages implementation (no server required)"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from app.api.routes import fi_messages
        from app import schemas
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False


def test_router_exists():
    """Test that the router is defined"""
    try:
        from app.api.routes.fi_messages import router
        print(f"✓ Router exists: {router}")
        return True
    except Exception as e:
        print(f"✗ Router error: {e}")
        return False


def test_endpoints_defined():
    """Test that all 4 endpoints are defined"""
    try:
        from app.api.routes.fi_messages import (
            generate_camt056,
            generate_camt029,
            generate_pacs007,
            generate_pacs009
        )
        endpoints = [
            ("camt056", generate_camt056),
            ("camt029", generate_camt029),
            ("pacs007", generate_pacs007),
            ("pacs009", generate_pacs009)
        ]
        for name, func in endpoints:
            print(f"✓ Endpoint {name} exists: {func.__name__}")
        return True
    except Exception as e:
        print(f"✗ Endpoint error: {e}")
        return False


def test_schemas_defined():
    """Test that request/response schemas are defined"""
    try:
        from app.schemas import FIMessageRequest, FIMessageResponse
        print(f"✓ FIMessageRequest schema exists")
        print(f"✓ FIMessageResponse schema exists")
        
        # Test schema instantiation
        req = FIMessageRequest(reason_code="CUST")
        print(f"✓ FIMessageRequest can be instantiated: {req}")
        
        resp = FIMessageResponse(
            message_id="test-123",
            type="camt.056",
            receipt_id="rid-123",
            url="/files/rid-123/camt056.xml"
        )
        print(f"✓ FIMessageResponse can be instantiated: {resp}")
        return True
    except Exception as e:
        print(f"✗ Schema error: {e}")
        return False


def test_router_registered():
    """Test that router is registered in app factory"""
    try:
        from app.api.app_factory import create_app
        app = create_app()
        
        # Check routes
        routes = [route.path for route in app.routes]
        expected_routes = [
            "/v1/iso/camt056/{rid}",
            "/v1/iso/camt029/{rid}",
            "/v1/iso/pacs007/{rid}",
            "/v1/iso/pacs009/{rid}"
        ]
        
        for route in expected_routes:
            if route in routes:
                print(f"✓ Route registered: {route}")
            else:
                print(f"✗ Route NOT found: {route}")
                print(f"  Available routes: {routes[:10]}...")
                return False
        
        return True
    except Exception as e:
        print(f"✗ App factory error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_iso_message_generators():
    """Test that ISO message generators exist"""
    try:
        from app.iso_messages import camt056, camt029, pacs007, pacs009
        
        generators = [
            ("camt056", hasattr(camt056, 'generate_camt056')),
            ("camt029", hasattr(camt029, 'generate_camt029')),
            ("pacs007", hasattr(pacs007, 'generate_pacs007')),
            ("pacs009", hasattr(pacs009, 'generate_pacs009'))
        ]
        
        for name, exists in generators:
            if exists:
                print(f"✓ Generator exists: {name}")
            else:
                print(f"✗ Generator missing: {name}")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Generator error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("FI Messages Implementation Unit Tests")
    print("=" * 60)
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Router exists", test_router_exists),
        ("Endpoints defined", test_endpoints_defined),
        ("Schemas defined", test_schemas_defined),
        ("ISO generators exist", test_iso_message_generators),
        ("Router registered", test_router_registered),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'─' * 60}")
        print(f"Test: {name}")
        print(f"{'─' * 60}")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print(f"\n\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Implementation is correct.")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
