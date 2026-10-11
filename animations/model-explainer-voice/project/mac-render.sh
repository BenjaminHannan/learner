#!/bin/bash
# Render the silent picture chunks of the narrated explainer. Run from this folder on the Mac.
#   bash mac-render.sh                       renders every chunk (reverse order: ch14 end ch09 ... ch00) into ../renders-mac/
#   bash mac-render.sh ch14 ch09             only those chunks
# Needs Node 20+ and internet for the first run (npx fetches hyperframes 0.8.143 and its Chrome). Skips chunks that already exist.
cd "$(dirname "$0")" || exit 1
OUT=../renders-mac; mkdir -p "$OUT"
CH="${*:-ch14 end ch09 ch08 ch07 ch06 ch05 ch04 ch03 ch01 ch00}"
for c in $CH; do
  if [ -s "$OUT/$c.mp4" ]; then echo "have $c"; continue; fi
  s=$(date +%s)
  node tools/mkindex.mjs --only "$c" > /dev/null || exit 1
  npx --yes hyperframes@0.8.143 render --fps 30 --quality looks --workers "${HF_WORKERS:-6}" --quiet --output "$OUT/$c.mp4" . || { echo "render failed for $c" >&2; rm -f "$OUT/$c.mp4"; exit 1; }
  echo "rendered $c in $(( $(date +%s) - s )) s ($(ls -l "$OUT/$c.mp4" | awk '{print $5}') bytes)"
done
node tools/mkindex.mjs > /dev/null
