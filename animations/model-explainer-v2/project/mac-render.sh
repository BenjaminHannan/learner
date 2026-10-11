#!/bin/bash
# Render the v2 explainer picture chunks on the Mac and push each one to branch claude/voice-render-mac3.
#   bash mac-render.sh                 renders the default list (longest first), skipping chunks already rendered or claimed by the cloud
#   bash mac-render.sh ch05 ch04       only those
# Run from this folder (animations/model-explainer-v2/project) inside a checkout of claude/voice-render-mac3.
cd "$(dirname "$0")" || exit 1
export PATH=/opt/homebrew/bin:$PATH
BR=claude/voice-render-mac3
OUT=../renders; mkdir -p "$OUT" ../claims
CH="${*:-ch05 ch04 ch03 ch07 ch08 ch01 ch06 ch00 ch09}"
sync() { git pull -q --rebase --autostash origin "$BR" >/dev/null 2>&1; }
push() { for i in 1 2 3 4 5; do sync; git push -q origin "HEAD:$BR" && return 0; sleep $((i*2)); done; echo "push failed" >&2; return 1; }
if [ $# -eq 0 ]; then
  echo "waiting for ../READY-ALL (the cloud pushes it when every part is timed)"
  for i in $(seq 1 120); do sync; [ -e ../READY-ALL ] && break; sleep 20; done
  [ -e ../READY-ALL ] || { echo "READY-ALL never came" >&2; exit 1; }
fi
for c in $CH; do
  sync
  if [ -s "$OUT/$c.mp4" ] || [ -e "../claims/$c" ]; then echo "skip $c (done or claimed)"; continue; fi
  echo mac > "../claims/$c"; git add "../claims/$c"; git commit -q -m "mac claims $c"; push
  s=$(date +%s)
  node tools/mkindex.mjs --only "$c" > /dev/null || exit 1
  npx --yes hyperframes@0.8.143 render --fps 30 --quality looks --workers "${HF_WORKERS:-6}" --quiet --output "$OUT/$c.mp4" . || { echo "render failed for $c" >&2; rm -f "$OUT/$c.mp4"; exit 1; }
  git checkout -q -- index.html 2>/dev/null
  git add "$OUT/$c.mp4"; git commit -q -m "mac render $c"; push
  echo "rendered $c in $(( $(date +%s) - s )) s ($(ls -l "$OUT/$c.mp4" | awk '{print $5}') bytes), pushed"
done
echo "MAC-RENDER-DONE"
