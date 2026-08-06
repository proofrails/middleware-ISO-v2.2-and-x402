#!/usr/bin/env python3
"""Create and poll a receipt. Requires an explicit write gate."""
import json, os, sys, time, urllib.error, urllib.request

base = os.getenv("PROOFRAILS_BASE_URL", "https://app.proofrails.com")
key = os.environ["PROOFRAILS_API_KEY"]
if os.getenv("PROOFRAILS_EXECUTE_RECEIPT_WRITE") != "yes":
    raise SystemExit("Receipt write gate is closed; set PROOFRAILS_EXECUTE_RECEIPT_WRITE=yes")

payload = {
    "tip_tx_hash": os.environ["PROOFRAILS_TX_HASH"],
    "chain": os.getenv("PROOFRAILS_CHAIN", "flare"),
    "amount": os.getenv("PROOFRAILS_AMOUNT", "12.50"),
    "currency": os.getenv("PROOFRAILS_CURRENCY", "USD₮0"),
    "sender_wallet": os.environ["PROOFRAILS_SENDER"],
    "receiver_wallet": os.environ["PROOFRAILS_RECEIVER"],
    "reference": os.environ["PROOFRAILS_REFERENCE"],
}

def request(url, *, method="GET", body=None, authenticated=False):
    headers = {"Content-Type": "application/json"}
    if authenticated:
        headers["X-API-Key"] = key
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        safe_body = error.read(4096).decode("utf-8", "replace")
        request_id = error.headers.get("X-Request-ID")
        raise RuntimeError(f"HTTP {error.code} request_id={request_id} body={safe_body}") from error

created = request(f"{base}/v1/iso/record-tip", method="POST", body=payload, authenticated=True)
receipt_id = created["receipt_id"]
print(f"receipt_id={receipt_id}")
for attempt in range(30):
    receipt = request(f"{base}/v1/iso/receipts/{receipt_id}")
    status = receipt["status"]
    if status == "anchored":
        print(json.dumps(receipt, indent=2)); sys.exit(0)
    if status == "failed":
        print(json.dumps(receipt, indent=2), file=sys.stderr); sys.exit(1)
    if status not in {"pending", "awaiting_anchor"}:
        raise RuntimeError(f"Unknown receipt status: {status}")
    time.sleep(min(2 ** attempt, 15))
raise SystemExit("Polling timeout; receipt state remains unresolved")
