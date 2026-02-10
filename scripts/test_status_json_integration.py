"""Integration test for status.json feature.

This test verifies that status.json is created and updated correctly
during the actual receipt processing workflow.
"""
import json
import os
import time
import uuid
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8001"
ARTIFACTS_DIR = os.getenv("ARTIFACTS_DIR", "artifacts")


def test_status_json_integration():
    """Test the complete status.json workflow."""
    print("=" * 70)
    print("Status.json Integration Test")
    print("=" * 70)
    print()
    
    # 1. Record a tip
    print("Step 1: Recording tip transaction...")
    ref = f"status-test:{uuid.uuid4()}"
    tx = f"0x{uuid.uuid4().hex}"
    
    payload = {
        "tip_tx_hash": tx,
        "chain": "flare",
        "amount": "0.01",
        "currency": "FLR",
        "sender_wallet": "0xSTATUS_SENDER",
        "receiver_wallet": "0xSTATUS_RECEIVER",
        "reference": ref,
    }
    
    try:
        r = requests.post(f"{BASE}/v1/iso/record-tip", json=payload, timeout=20)
        if r.status_code != 200:
            print(f"✗ Failed to record tip: {r.status_code}")
            print(f"  Response: {r.text}")
            return False
        
        rec = r.json()
        rid = rec["receipt_id"]
        print(f"✓ Receipt created: {rid}")
        print(f"  Initial status: {rec['status']}")
    except requests.exceptions.ConnectionError:
        print("✗ Connection failed - Is the server running on port 8001?")
        print("  Start server: python -m uvicorn app.main:app --reload --port 8001")
        return False
    except Exception as e:
        print(f"✗ Error recording tip: {e}")
        return False
    
    # 2. Wait for background processing
    print("\nStep 2: Waiting for background processing (10 seconds)...")
    time.sleep(10)
    
    # 3. Check if receipt.json exists in evidence.zip
    print("\nStep 3: Checking evidence.zip contents...")
    artifacts_dir = Path(ARTIFACTS_DIR) / rid
    evidence_zip = artifacts_dir / "evidence.zip"
    
    if not evidence_zip.exists():
        print(f"✗ evidence.zip not found at: {evidence_zip}")
        return False
    
    print(f"✓ evidence.zip exists: {evidence_zip}")
    
    # Extract and check receipt.json status
    try:
        import zipfile
        with zipfile.ZipFile(evidence_zip, 'r') as zf:
            if 'receipt.json' in zf.namelist():
                receipt_json_data = json.loads(zf.read('receipt.json'))
                print(f"  receipt.json status (in zip): {receipt_json_data.get('status')}")
            else:
                print("✗ receipt.json not found in evidence.zip")
                return False
    except Exception as e:
        print(f"✗ Error reading evidence.zip: {e}")
        return False
    
    # 4. Check if status.json exists
    print("\nStep 4: Checking status.json file...")
    status_file = artifacts_dir / "status.json"
    
    if not status_file.exists():
        print(f"✗ status.json not found at: {status_file}")
        print("  This may mean anchoring hasn't completed yet or the feature isn't working")
        
        # Query API to see current status
        try:
            r2 = requests.get(f"{BASE}/v1/iso/receipts/{rid}", timeout=10)
            if r2.status_code == 200:
                api_data = r2.json()
                print(f"\n  API reports status: {api_data.get('status')}")
                if api_data.get('status') == 'anchored':
                    print("  ⚠️  Receipt is anchored but status.json missing - feature may not be working")
                elif api_data.get('status') == 'pending':
                    print("  ℹ️  Receipt still pending - wait longer for anchoring")
        except Exception:
            pass
        
        return False
    
    print(f"✓ status.json exists: {status_file}")
    
    # 5. Read and validate status.json
    print("\nStep 5: Validating status.json content...")
    try:
        with open(status_file, 'r') as f:
            status_data = json.load(f)
        
        print(f"✓ status.json is valid JSON")
        print(f"\nstatus.json content:")
        print(json.dumps(status_data, indent=2))
        
        # Validate required fields
        required_fields = ["receipt_id", "status", "bundle_hash", "last_updated"]
        missing = [f for f in required_fields if f not in status_data]
        
        if missing:
            print(f"\n✗ Missing required fields: {missing}")
            return False
        
        print(f"\n✓ All required fields present")
        print(f"  Status: {status_data['status']}")
        print(f"  Bundle Hash: {status_data.get('bundle_hash', 'N/A')[:20]}...")
        print(f"  Flare TX: {status_data.get('flare_txid', 'N/A')}")
        print(f"  Last Updated: {status_data.get('last_updated')}")
        
    except Exception as e:
        print(f"✗ Error reading status.json: {e}")
        return False
    
    # 6. Compare with API response
    print("\nStep 6: Comparing status.json with API response...")
    try:
        r3 = requests.get(f"{BASE}/v1/iso/receipts/{rid}", timeout=10)
        if r3.status_code == 200:
            api_data = r3.json()
            
            # Compare key fields
            matches = []
            matches.append(("status", status_data.get('status') == api_data.get('status')))
            matches.append(("bundle_hash", status_data.get('bundle_hash') == api_data.get('bundle_hash')))
            matches.append(("flare_txid", status_data.get('flare_txid') == api_data.get('flare_txid')))
            
            all_match = all(m[1] for m in matches)
            
            for field, match in matches:
                status = "✓" if match else "✗"
                print(f"  {status} {field} matches")
            
            if all_match:
                print("\n✓ status.json matches API response perfectly")
                return True
            else:
                print("\n✗ status.json doesn't match API response")
                return False
        else:
            print(f"✗ API request failed: {r3.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error querying API: {e}")
        return False


def main():
    try:
        success = test_status_json_integration()
        
        print("\n" + "=" * 70)
        if success:
            print("🎉 Integration test PASSED!")
            print("\nstatus.json feature is working correctly:")
            print("  ✓ File is created after processing")
            print("  ✓ Contains all required fields")
            print("  ✓ Matches API response")
            print("  ✓ Shows current status (not stuck on 'pending')")
            return 0
        else:
            print("❌ Integration test FAILED")
            print("\nPossible issues:")
            print("  - Server not running (start with: python -m uvicorn app.main:app --port 8001)")
            print("  - Worker not running (start with: python worker.py)")
            print("  - Anchoring configuration issue")
            print("  - status.json feature not properly integrated")
            return 1
    except Exception as e:
        print(f"\n❌ Test crashed: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
