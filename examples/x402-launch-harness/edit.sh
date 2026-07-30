#!/usr/bin/env bash
# Burn the launch-video titles, captions and the persistent mainnet label onto a
# raw screen recording. Nothing here changes, re-orders or fabricates terminal
# output.
set -euo pipefail

RAW=${1:?usage: edit.sh raw.mp4 final.mp4}
OUT=${2:?usage: edit.sh raw.mp4 final.mp4}
FONT=${FONT:-/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf}
FONT_REG=${FONT_REG:-/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf}

t() { # text, fontfile, size, y, start, end, extra
  printf "drawtext=fontfile=%s:text='%s':fontsize=%s:fontcolor=white:x=(w-text_w)/2:y=%s:box=1:boxcolor=black@0.72:boxborderw=18:enable='between(t,%s,%s)'" \
    "$2" "$1" "$3" "$4" "$5" "$6"
}

FILTER="$(t 'A paid API call, with the receipt built in.' "$FONT" 64 '(h/2)-70' 0 6.5)"
FILTER="$FILTER,$(t 'x402 payment · delivered result · signed evidence · Flare anchor' "$FONT_REG" 38 '(h/2)+30' 0.6 6.5)"
FILTER="$FILTER,$(t 'The API declares the exact payment terms before authorization.' "$FONT_REG" 38 'h-160' 9 18)"
FILTER="$FILTER,$(t 'Payment and delivery now share one traceable receipt reference.' "$FONT_REG" 38 'h-160' 33 41)"
FILTER="$FILTER,$(t 'ProofRails' "$FONT" 72 '(h/2)-110' 89 99)"
FILTER="$FILTER,$(t 'Verifiable receipts for onchain payments and paid API calls.' "$FONT_REG" 40 '(h/2)-10' 89 99)"
FILTER="$FILTER,$(t 'Settlement is only the beginning of the record.' "$FONT_REG" 36 '(h/2)+60' 91 99)"
FILTER="$FILTER,$(t 'proofrails.com' "$FONT" 44 '(h/2)+140' 93 99)"

# Persistent label during the payment sequence.
FILTER="$FILTER,drawtext=fontfile=$FONT:text='FLARE MAINNET · REAL VALUE · 0.001 USD₮0':fontsize=32:fontcolor=white:x=w-text_w-48:y=48:box=1:boxcolor=black@0.75:boxborderw=14:enable='between(t,19,70)'"

ffmpeg -y -i "$RAW" -vf "$FILTER" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -an "$OUT"
echo "wrote $OUT"
