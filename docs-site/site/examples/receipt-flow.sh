#!/usr/bin/env bash
set -euo pipefail

: "${PROOFRAILS_BASE_URL:=https://app.proofrails.com}"
: "${PROOFRAILS_API_KEY:?Set PROOFRAILS_API_KEY in a secret-aware environment}"
: "${PROOFRAILS_TX_HASH:?Set the existing settlement transaction hash}"
: "${PROOFRAILS_REFERENCE:?Set a stable business reference}"
: "${PROOFRAILS_EXECUTE_RECEIPT_WRITE:?Set to yes after reviewing the request}"

if [[ "$PROOFRAILS_EXECUTE_RECEIPT_WRITE" != "yes" ]]; then
  printf '%s
' 'Receipt write gate is closed.' >&2
  exit 2
fi

payload=$(python3 -c 'import json,os; print(json.dumps({"tip_tx_hash":os.environ["PROOFRAILS_TX_HASH"],"chain":os.getenv("PROOFRAILS_CHAIN","flare"),"amount":os.getenv("PROOFRAILS_AMOUNT","12.50"),"currency":os.getenv("PROOFRAILS_CURRENCY","USD₮0"),"sender_wallet":os.environ["PROOFRAILS_SENDER"],"receiver_wallet":os.environ["PROOFRAILS_RECEIVER"],"reference":os.environ["PROOFRAILS_REFERENCE"]}))')

response=$(curl --fail-with-body --silent --show-error   --request POST "$PROOFRAILS_BASE_URL/v1/iso/record-tip"   --header "X-API-Key: $PROOFRAILS_API_KEY"   --header 'Content-Type: application/json'   --data "$payload")

receipt_id=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["receipt_id"])' <<<"$response")
printf 'receipt_id=%s
' "$receipt_id"

for attempt in $(seq 1 30); do
  receipt=$(curl --fail --silent --show-error "$PROOFRAILS_BASE_URL/v1/iso/receipts/$receipt_id")
  status=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' <<<"$receipt")
  case "$status" in
    anchored) printf '%s
' "$receipt"; exit 0 ;;
    failed) printf '%s
' "$receipt" >&2; exit 1 ;;
    pending|awaiting_anchor) sleep 5 ;;
    *) printf 'Unknown status: %s
' "$status" >&2; exit 1 ;;
  esac
done
printf '%s
' 'Polling timeout; receipt state remains unresolved.' >&2
exit 1
