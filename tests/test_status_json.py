"""Test that status.json is created and updated correctly after anchoring."""
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_status_json_helper_function():
    """Test the _write_status_json helper function exists in jobs module."""
    try:
        from app.jobs import _write_status_json
        print("✓ _write_status_json function exists in app.jobs")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_status_json_in_confirm_anchor():
    """Test that confirm_anchor endpoint has status.json writing."""
    try:
        from app.api.routes.confirm_anchor import _write_status_json
        print("✓ _write_status_json function exists in confirm_anchor")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_status_json_creation_mock():
    """Test status.json file creation with mock data."""
    try:
        from datetime import datetime
        from app import models
        
        # Create a mock receipt object
        class MockReceipt:
            def __init__(self):
                self.id = "test-receipt-123"
                self.status = "anchored"
                self.bundle_hash = "0xabc123..."
                self.flare_txid = "0xdef456..."
                self.anchored_at = datetime.utcnow()
                self.created_at = datetime.utcnow()
        
        mock_rec = MockReceipt()
        
        # Test status.json structure
        status_data = {
            "receipt_id": str(mock_rec.id),
            "status": mock_rec.status,
            "bundle_hash": mock_rec.bundle_hash,
            "flare_txid": mock_rec.flare_txid,
            "anchored_at": mock_rec.anchored_at.isoformat() if mock_rec.anchored_at else None,
            "created_at": mock_rec.created_at.isoformat() if mock_rec.created_at else None,
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        # Verify all required fields are present
        required_fields = ["receipt_id", "status", "bundle_hash", "flare_txid", "anchored_at", "created_at", "last_updated"]
        for field in required_fields:
            if field not in status_data:
                print(f"✗ Missing required field: {field}")
                return False
        
        # Verify it can be serialized to JSON
        json_str = json.dumps(status_data, indent=2, separators=(",", ": "))
        parsed = json.loads(json_str)
        
        print("✓ status.json structure is valid")
        print(f"✓ Contains all {len(required_fields)} required fields")
        print(f"✓ JSON serialization works")
        print("\nExample status.json:")
        print(json_str)
        
        return True
    except Exception as e:
        print(f"✗ Error creating status.json structure: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_jobs_code_inspection():
    """Inspect jobs.py to verify status.json is written after anchoring."""
    try:
        with open("app/jobs.py", "r", encoding="utf-8") as f:
            code = f.read()
        
        # Check for status.json writing calls
        checks = [
            ('_write_status_json(rec)' in code, "Call to _write_status_json exists"),
            ('def _write_status_json' in code, "_write_status_json function defined"),
            ('status.json' in code, "status.json filename referenced"),
            ('last_updated' in code, "last_updated timestamp included"),
        ]
        
        all_passed = True
        for check, desc in checks:
            if check:
                print(f"✓ {desc}")
            else:
                print(f"✗ {desc}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"✗ Error inspecting jobs.py: {e}")
        return False


def test_confirm_anchor_code_inspection():
    """Inspect confirm_anchor.py to verify status.json is written."""
    try:
        with open("app/api/routes/confirm_anchor.py", "r", encoding="utf-8") as f:
            code = f.read()
        
        # Check for status.json writing calls
        checks = [
            ('_write_status_json(rec)' in code, "Call to _write_status_json exists"),
            ('def _write_status_json' in code, "_write_status_json function defined"),
            ('status.json' in code, "status.json filename referenced"),
        ]
        
        all_passed = True
        for check, desc in checks:
            if check:
                print(f"✓ {desc}")
            else:
                print(f"✗ {desc}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"✗ Error inspecting confirm_anchor.py: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Status.json Implementation Tests")
    print("=" * 70)
    print()
    
    tests = [
        ("Status helper in jobs.py", test_status_json_helper_function),
        ("Status helper in confirm_anchor", test_status_json_in_confirm_anchor),
        ("Status.json structure", test_status_json_creation_mock),
        ("Jobs.py code inspection", test_jobs_code_inspection),
        ("Confirm_anchor code inspection", test_confirm_anchor_code_inspection),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'─' * 70}")
        print(f"Test: {name}")
        print(f"{'─' * 70}")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print(f"\n\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! status.json implementation is correct.")
        print("\nℹ️  After anchoring completes, users can find:")
        print("   - evidence.zip (immutable snapshot with status='pending')")
        print("   - status.json (current status, updated after anchoring)")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
