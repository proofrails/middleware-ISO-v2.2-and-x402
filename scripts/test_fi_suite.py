import json
import time
import uuid

import requests

BASE = "http://127.0.0.1:8001"


def get(url, **kw):
    tries = kw.get("tries", 5)
    delay = kw.get("delay", 1)
    last_exc = None
    for _ in range(tries):
        try:
            r = requests.get(url, timeout=kw.get("timeout", 20))
            try:
                body = r.json()
            except Exception:
                body = r.text
            return r.status_code, body, r.headers.get("content-type", "")
        except Exception as e:
            last_exc = e
            time.sleep(delay)
    # Final attempt raises
    raise last_exc


def post(url, payload=None, **kw):
    tries = kw.get("tries", 5)
    delay = kw.get("delay", 1)
    last_exc = None
    for _ in range(tries):
        try:
            r = requests.post(url, json=payload, timeout=kw.get("timeout", 20))
            try:
                body = r.json()
            except Exception:
                body = r.text
            return r.status_code, body, r.headers.get("content-type", "")
        except Exception as e:
            last_exc = e
            time.sleep(delay)
    raise last_exc


def main():
    # 1) Record a tip
    ref = f"fi-suite:{uuid.uuid4()}"
    tx = f"0x{uuid.uuid4().hex}"
    payload = {
        "tip_tx_hash": tx,
        "chain": "flare",
        "amount": "0.01",
        "currency": "FLR",
        "sender_wallet": "0xFI_SND",
        "receiver_wallet": "0xFI_RCV",
        "reference": ref,
    }
    code, rec, _ = post(f"{BASE}/v1/iso/record-tip", payload, timeout=25)
    print("RECORD", code, rec)
    if code != 200 or not isinstance(rec, dict):
        return 1
    rid = rec["receipt_id"]

    # 2) Wait for background to create pain.001 etc.
    time.sleep(4)
    code, arts, _ = get(f"{BASE}/v1/iso/messages/{rid}")
    print("ARTS_BEFORE", code)
    print(json.dumps(arts, indent=2))

    # 3) Generate FI artifacts in separate calls (avoid connection resets on long pipelines)
    code, b1, _ = post(f"{BASE}/v1/iso/camt056/{rid}", {"reason_code": "CUST"})
    print("C056", code, b1)
    code, b2, _ = post(f"{BASE}/v1/iso/camt029/{rid}", {"resolution_code": "APPR"})
    print("C029", code, b2)
    code, b3, _ = post(f"{BASE}/v1/iso/pacs007/{rid}", {"reason_code": "CUST"})
    print("P007", code, b3)
    code, b4, _ = post(f"{BASE}/v1/iso/pacs009/{rid}")
    print("P009", code, b4)

    # 4) Re-list artifacts
    time.sleep(1)
    code, arts2, _ = get(f"{BASE}/v1/iso/messages/{rid}")
    print("ARTS_AFTER", code)
    print(json.dumps(arts2, indent=2))

    # 5) Basic checks
    have = {a.get("type") for a in (arts2 if isinstance(arts2, list) else [])}
    print("HAVE_TYPES", sorted(have))
    expected = {"camt.056", "camt.029", "pacs.007", "pacs.009"}
    missing = expected - have
    print("MISSING", sorted(missing))
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
