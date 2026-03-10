import json
import time
import uuid

import requests

BASE = "http://127.0.0.1:8001"


def put_json(url, payload, timeout=20):
    r = requests.put(url, json=payload, timeout=timeout)
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body


def get_json(url, timeout=20):
    r = requests.get(url, timeout=timeout)
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body


def post_json(url, payload=None, timeout=20):
    r = requests.post(url, json=payload, timeout=timeout)
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body


def main():
    # Enable pacs.002 emission via config (PUT)
    code, cfg = get_json(f"{BASE}/v1/config")
    print("GET_CONFIG", code)
    if code != 200 or not isinstance(cfg, dict):
        print("Config fetch failed:", cfg)
        return 1
    cfg.setdefault("status", {})["emit_pacs002"] = True
    code, body = put_json(f"{BASE}/v1/config", cfg)
    print("PUT_CONFIG", code, body if code != 200 else "OK")

    # Record a tip
    ref = f"interbank:{uuid.uuid4()}"
    tx = f"0x{uuid.uuid4().hex}"
    payload = {
        "tip_tx_hash": tx,
        "chain": "flare",
        "amount": "0.000000000000000001",
        "currency": "FLR",
        "sender_wallet": "0xIB_SND",
        "receiver_wallet": "0xIB_RCV",
        "reference": ref,
    }
    code, rec = post_json(f"{BASE}/v1/iso/record-tip", payload, timeout=25)
    print("RECORD_TIP", code, rec)
    if code != 200 or not isinstance(rec, dict):
        return 1
    rid = rec["receipt_id"]

    # Wait for background tasks
    time.sleep(3)

    # List artifacts and check for pacs.002
    code, arts = get_json(f"{BASE}/v1/iso/messages/{rid}")
    print("MESSAGES", code)
    print(json.dumps(arts, indent=2))
    have_pacs002 = any(a.get("type") == "pacs.002" for a in (arts if isinstance(arts, list) else []))
    print("HAVE_PACS002", have_pacs002)

    # Generate pacs.008 on demand
    code, gen = post_json(f"{BASE}/v1/iso/pacs008/{rid}", {})
    print("GEN_PACS008", code, gen)

    # Re-list artifacts to confirm pacs.008
    code, arts2 = get_json(f"{BASE}/v1/iso/messages/{rid}")
    print("MESSAGES_AFTER_PACS008", code)
    print(json.dumps(arts2, indent=2))
    have_pacs008 = any(a.get("type") == "pacs.008" for a in (arts2 if isinstance(arts2, list) else []))
    print("HAVE_PACS008", have_pacs008)

    print("\nINTERBANK_TEST_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
