import json
import sys
import time
import uuid

import requests

BASE = "http://127.0.0.1:8001"


def pp(title, obj):
    try:
        s = json.dumps(obj, indent=2, default=str)
    except Exception:
        s = str(obj)
    print(f"== {title} ==")
    print(s)


def get_json(url, **kw):
    r = requests.get(url, timeout=kw.get("timeout", 20))
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text)


def post_json(url, payload, **kw):
    r = requests.post(url, json=payload, timeout=kw.get("timeout", 20))
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text)


def main():
    results = {}

    # 1) Liveness
    code, body = get_json(f"{BASE}/v1/health", timeout=10)
    results["health"] = {"status": code, "body": body}
    print("HEALTH", code, body)
    try:
        ping = requests.get(f"{BASE}/v1/ping", timeout=5)
        results["ping"] = {"status": ping.status_code, "body": ping.text}
        print("PING", ping.status_code, ping.text)
    except Exception as e:
        results["ping"] = {"error": str(e)}

    # 2) Config round-trip: enable structured remittance
    code, cfg = get_json(f"{BASE}/v1/config")
    results["get_config_before"] = {"status": code, "cfg": cfg}
    if code != 200 or not isinstance(cfg, dict):
        print("GET CONFIG failed")
        pp("get_config_before", results["get_config_before"])
        sys.exit(1)
    cfg.setdefault("mapping", {})["structured_remittance"] = True
    code, put = post_json(f"{BASE}/v1/config", cfg)
    results["put_config"] = {"status": code, "cfg": put}
    print("PUT CONFIG", code)

    # 3) Record a tip
    ref = f"regression:{uuid.uuid4()}"
    tx = f"0x{uuid.uuid4().hex}"
    payload = {
        "tip_tx_hash": tx,
        "chain": "flare",
        "amount": "0.000000000000000001",
        "currency": "FLR",
        "sender_wallet": "0xREG_SND",
        "receiver_wallet": "0xREG_RCV",
        "reference": ref,
    }
    code, rec = post_json(f"{BASE}/v1/iso/record-tip", payload, timeout=25)
    results["record_tip"] = {"status": code, "body": rec}
    print("RECORD", code, rec)
    if code != 200 or not isinstance(rec, dict):
        sys.exit(1)
    rid = rec["receipt_id"]

    # wait background
    time.sleep(3)

    # 4) List artifacts (original)
    code, arts = get_json(f"{BASE}/v1/iso/messages/{rid}")
    results["messages_orig"] = {"status": code, "artifacts": arts}
    print("MESSAGES_ORIG", code)
    pp("ARTS_ORIG", arts)

    # 5) Get receipt and verify (by bundle_url if present)
    code, rcp = get_json(f"{BASE}/v1/iso/receipts/{rid}")
    results["receipt_orig"] = {"status": code, "receipt": rcp}
    print("RECEIPT_ORIG", code)
    pp("RECEIPT_ORIG", rcp)

    bundle_url = None
    if isinstance(rcp, dict) and rcp.get("bundle_url"):
        # Construct full URL if needed
        bu = rcp["bundle_url"]
        bundle_url = bu if bu.startswith("http") else (BASE + bu)
    if bundle_url:
        code, ver = post_json(f"{BASE}/v1/iso/verify", {"bundle_url": bundle_url})
        results["verify_orig"] = {"status": code, "verify": ver}
        print("VERIFY_ORIG", code)
        pp("VERIFY_ORIG", ver)

    # 6) Cancel flow (pain.007 + pacs.004)
    code, can = post_json(f"{BASE}/v1/iso/cancel", {"original_receipt_id": rid, "reason_code": "CUST"}, timeout=25)
    results["cancel"] = {"status": code, "body": can}
    print("CANCEL", code, can)
    if code != 200 or not isinstance(can, dict):
        sys.exit(1)
    refund_rid = can["refund_receipt_id"]

    time.sleep(3)

    # 7) Artifacts for refund receipt
    code, arts_ref = get_json(f"{BASE}/v1/iso/messages/{refund_rid}")
    results["messages_refund"] = {"status": code, "artifacts": arts_ref}
    print("MESSAGES_REFUND", code)
    pp("ARTS_REFUND", arts_ref)

    # 8) Refund receipt
    code, rcp_ref = get_json(f"{BASE}/v1/iso/receipts/{refund_rid}")
    results["receipt_refund"] = {"status": code, "receipt": rcp_ref}
    print("RECEIPT_REFUND", code)
    pp("RECEIPT_REFUND", rcp_ref)

    # 9) Verify refund bundle if present
    bundle_url_ref = None
    if isinstance(rcp_ref, dict) and rcp_ref.get("bundle_url"):
        bu2 = rcp_ref["bundle_url"]
        bundle_url_ref = bu2 if bu2.startswith("http") else (BASE + bu2)
    if bundle_url_ref:
        code, ver2 = post_json(f"{BASE}/v1/iso/verify", {"bundle_url": bundle_url_ref})
        results["verify_refund"] = {"status": code, "verify": ver2}
        print("VERIFY_REFUND", code)
        pp("VERIFY_REFUND", ver2)

    # 10) Idempotent cancel (should return same refund id)
    code, can2 = post_json(f"{BASE}/v1/iso/cancel", {"original_receipt_id": rid, "reason_code": "CUST"})
    results["cancel_idempotent"] = {"status": code, "body": can2}
    print("CANCEL_AGAIN", code, can2)

    # 11) Anchors view (will be empty unless anchoring is configured)
    code, anch_o = get_json(f"{BASE}/v1/anchors/{rid}")
    results["anchors_orig"] = {"status": code, "anchors": anch_o}
    print("ANCHORS_ORIG", code, anch_o)

    code, anch_r = get_json(f"{BASE}/v1/anchors/{refund_rid}")
    results["anchors_refund"] = {"status": code, "anchors": anch_r}
    print("ANCHORS_REFUND", code, anch_r)

    print("\nSUMMARY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
