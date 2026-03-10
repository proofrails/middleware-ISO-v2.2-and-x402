import json
import time
import uuid

import requests

BASE = "http://127.0.0.1:8001"  # adjust if server is on a different port


def main():
    # Health
    try:
        h = requests.get(f"{BASE}/v1/health", timeout=10)
        print("HEALTH", h.status_code, h.text)
    except Exception as e:
        print("HEALTH_FAIL", e)
        return

    # Read and update config to enable structured remittance
    try:
        cfg = requests.get(f"{BASE}/v1/config", timeout=10).json()
        cfg.setdefault("mapping", {})["structured_remittance"] = True
        r = requests.put(f"{BASE}/v1/config", json=cfg, timeout=10)
        print("PUT_CFG", r.status_code)
    except Exception as e:
        print("PUT_CFG_FAIL", e)
        return

    # Record a tip to generate pain.001 (+ remt.001 when toggle true)
    ref = f"demo:cancel:{uuid.uuid4()}"
    tx = f"0x{uuid.uuid4().hex}"
    payload = {
        "tip_tx_hash": tx,
        "chain": "flare",
        "amount": "0.000000000000000001",
        "currency": "FLR",
        "sender_wallet": "0xSND",
        "receiver_wallet": "0xRCV",
        "reference": ref,
    }
    r = requests.post(f"{BASE}/v1/iso/record-tip", json=payload, timeout=20)
    print("RECORD", r.status_code, r.text)
    if not r.ok:
        return
    rid = r.json()["receipt_id"]

    # Let background task produce artifacts
    time.sleep(3)
    arts = requests.get(f"{BASE}/v1/iso/messages/{rid}", timeout=20).json()
    print("ARTS_ORIG", json.dumps(arts, indent=2))

    # Cancel the original receipt: expect pain.007 on original, pacs.004 on refund receipt
    cr = requests.post(
        f"{BASE}/v1/iso/cancel",
        json={"original_receipt_id": rid, "reason_code": "CUST"},
        timeout=20,
    )
    print("CANCEL", cr.status_code, cr.text)
    if not cr.ok:
        return
    cancel_resp = cr.json()
    refund_rid = cancel_resp["refund_receipt_id"]

    # Let background process refund
    time.sleep(3)
    arts_ref = requests.get(f"{BASE}/v1/iso/messages/{refund_rid}", timeout=20).json()
    print("ARTS_REFUND", json.dumps(arts_ref, indent=2))

    # Also re-list original to check pain.007 presence
    arts2 = requests.get(f"{BASE}/v1/iso/messages/{rid}", timeout=20).json()
    print("ARTS_ORIG_2", json.dumps(arts2, indent=2))

    print("DONE")


if __name__ == "__main__":
    main()
