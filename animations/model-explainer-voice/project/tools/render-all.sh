#!/bin/bash
# Render the assembled video chapter by chapter (resumable), then join with ffmpeg.
#   tools/render-all.sh [OUTDIR]        run from the assembled project folder (content.js already merged)
# Each chunk is built with `mkindex --only <chapter>`; the progress bar keeps its global position.
set -e
OUT="${1:-renders}"; mkdir -p "$OUT"
CH=$(node -e "const w={};require('vm').runInNewContext(require('fs').readFileSync('content.js','utf8'),{window:w});console.log(w.CONTENT.order.join(' '))")
LIST="$OUT/list.txt"; : > "$LIST"
for c in $CH end; do
  if [ ! -s "$OUT/$c.mp4" ]; then
    node tools/mkindex.mjs --only "$c" >/dev/null
    npx --yes hyperframes@0.8.143 render --fps 30 --quality "${HF_QUALITY:-looks}" --workers "${HF_WORKERS:-3}" --quiet --output "$OUT/$c.mp4" . || { echo "render failed for $c" >&2; rm -f "$OUT/$c.mp4"; exit 1; }
    echo "rendered $c $(date +%H:%M:%S)"
  fi
  echo "file '$(cd "$OUT" && pwd)/$c.mp4'" >> "$LIST"
done
node tools/mkindex.mjs >/dev/null
ffmpeg -y -loglevel error -f concat -safe 0 -i "$LIST" -c copy "$OUT/model-explainer-main.mp4"
ls -la "$OUT/model-explainer-main.mp4"
