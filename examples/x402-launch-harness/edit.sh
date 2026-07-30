#!/usr/bin/env bash
# Build the launch video from ONE raw screen recording: cut the idle gaps, burn
# titles/captions and the persistent mainnet label. Segments are only trimmed and
# kept in capture order - no reordering, no re-timing, no fabricated output.
#
#   usage: edit.sh raw.mkv final.mp4 [segments-file]
#
# A segments file is a list of `start end caption` lines (seconds, in capture
# order). Without one, the defaults below reproduce the 2026-07-30 launch cut of
# runs/run-bd57cf7c-ba36-40c9-84c2-5dc67c8ccbbe.json.
set -euo pipefail

RAW=${1:?usage: edit.sh raw.mkv final.mp4 [segments-file]}
OUT=${2:?usage: edit.sh raw.mkv final.mp4 [segments-file]}
PLAN=${3:-}
FONT=${FONT:-/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf}
FONT_REG=${FONT_REG:-/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf}
LABEL=${LABEL:-'FLARE MAINNET · REAL VALUE · 0.001 USD₮0'}

DEFAULT_PLAN=$(
  cat <<'EOF'
30 44 The API states the exact payment terms before anything is signed.
49 58 One approved authorization, signed by the payer with the official x402 client.
58 63 Same endpoint, same request: the paid result is delivered with a PAYMENT-RESPONSE.
63 80 Receipt, evidence bundle and Flare anchor, verified independently from the served files.
129 138 The receipt is public: anchored, with the bundle hash it commits to.
143 155 Flare mainnet: 0.001 USD₮0 from the payer to the recipient through the facilitator.
164 173 The bundle hash is anchored onchain by the EvidenceAnchor contract.
EOF
)

esc() { printf '%s' "$1" | sed -e "s/\\\\/\\\\\\\\/g" -e "s/:/\\\\:/g" -e "s/'/\\\\\\\\\\\\'/g"; }

card() { # text, font, size, y, fade-in
  printf "drawtext=fontfile=%s:text='%s':fontsize=%s:fontcolor=white:x=(w-text_w)/2:y=%s:alpha='min(1,max(0,(t-%s)/0.6))'" \
    "$2" "$(esc "$1")" "$3" "$4" "$5"
}

TITLE_FILTER="$(card 'A paid API call, with the receipt built in.' "$FONT" 78 '(h/2)-90' 0.2)"
TITLE_FILTER="$TITLE_FILTER,$(card 'x402 payment · delivered result · signed evidence · Flare anchor' "$FONT_REG" 44 '(h/2)+40' 1.0)"

CLOSE_FILTER="$(card 'ProofRails' "$FONT" 86 '(h/2)-150' 0.2)"
CLOSE_FILTER="$CLOSE_FILTER,$(card 'Verifiable receipts for onchain payments and paid API calls.' "$FONT_REG" 46 '(h/2)-30' 0.8)"
CLOSE_FILTER="$CLOSE_FILTER,$(card 'An onchain anchor proves integrity and timing of the committed hash,' "$FONT_REG" 34 '(h/2)+70' 1.6)"
CLOSE_FILTER="$CLOSE_FILTER,$(card 'not the truth or legal sufficiency of offchain data.' "$FONT_REG" 34 '(h/2)+120' 1.6)"
CLOSE_FILTER="$CLOSE_FILTER,$(card 'proofrails.com' "$FONT" 48 '(h/2)+220' 2.4)"

filter="[1:v]${TITLE_FILTER}[title];[2:v]${CLOSE_FILTER}[close];"
labels="[title]"
i=0
while read -r start end caption; do
  [ -z "${start:-}" ] && continue
  cap="drawtext=fontfile=$FONT_REG:text='$(esc "$caption")':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=h-150:box=1:boxcolor=black@0.78:boxborderw=20"
  tag="drawtext=fontfile=$FONT:text='$(esc "$LABEL")':fontsize=34:fontcolor=white:x=w-text_w-56:y=52:box=1:boxcolor=black@0.78:boxborderw=16"
  filter="${filter}[0:v]trim=start=${start}:end=${end},setpts=PTS-STARTPTS,${cap},${tag}[s${i}];"
  labels="${labels}[s${i}]"
  i=$((i + 1))
done <<<"$([ -n "$PLAN" ] && cat "$PLAN" || printf '%s\n' "$DEFAULT_PLAN")"

filter="${filter}${labels}[close]concat=n=$((i + 2)):v=1:a=0[v]"

ffmpeg -y -i "$RAW" \
  -f lavfi -i "color=c=0x0b0f14:s=2560x1440:r=15:d=6" \
  -f lavfi -i "color=c=0x0b0f14:s=2560x1440:r=15:d=8" \
  -filter_complex "$filter" -map '[v]' \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -r 15 -an "$OUT"

ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT" | xargs printf 'wrote %s (%s s)\n' "$OUT"
