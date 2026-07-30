#!/usr/bin/env bash
set -euo pipefail
receipt_id=${1:-dec5a106-3216-4543-bfb6-e669dc83f4d7}
base=https://app.proofrails.com
curl --fail --silent --show-error "$base/v1/iso/receipts/$receipt_id" > receipt.json
bundle_url=$(python3 -c 'import json; print(json.load(open("receipt.json"))["bundle_url"])')
curl --fail --silent --show-error "$bundle_url" --output evidence.zip
sha256sum evidence.zip
python3 -c 'import zipfile; assert zipfile.ZipFile("evidence.zip").testzip() is None'
