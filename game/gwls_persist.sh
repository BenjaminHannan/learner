#!/bin/bash
# DRAFT pending coordinator confirmation (GW-LS). Copies the GW-LS outputs from the /tmp scratch folder to a permanent place (no git operation; the
# session lead commits): every iter-k.json and run.log of both seeds, and report.json / report.md.
# Run it after each round (and once more when the run ends). Safe to repeat: copies only, never deletes, never touches the training folder.
#
#   bash game/gwls_persist.sh [SRC_ROOT] [DEST]
#   defaults: SRC_ROOT = the scratch gwls folder, DEST = game/results/gwls/ of this repo
SCR=/tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad
SRC=${1:-$SCR/gwls}
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST=${2:-$HERE/results/gwls}
n=0
for seed in 200 201; do
  mkdir -p "$DEST/s$seed"
  for f in "$SRC"/s$seed/iter-*.json "$SRC"/s$seed/run.log; do
    [ -f "$f" ] && cp -p "$f" "$DEST/s$seed/" && n=$((n + 1))
  done
done
for f in "$SRC"/report.json "$SRC"/report.md; do
  [ -f "$f" ] && cp -p "$f" "$DEST/" && n=$((n + 1))
done
echo "persisted $n files from $SRC to $DEST"
