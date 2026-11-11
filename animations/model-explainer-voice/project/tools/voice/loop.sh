#!/bin/bash
# Pace all scenes to the narration, then make sure no picture runs past its scene; repeat until none does.
#   bash tools/voice/loop.sh BASE_CONTENT_DIR WORK_DIR [rounds]
# BASE_CONTENT_DIR = a copy of content/ from before narration timing. WORK_DIR = a scratch folder on a local disk (a copy of the project is built there).
# Needs VOICE_AUDIO_DIR (clips + index.json), node, python3, and Playwright's Chromium (see extent.mjs).
set -e
BASE="$1"; WORK="$2"; ROUNDS="${3:-4}"
cd "$(dirname "$0")/../.."
mkdir -p narration
for i in $(seq 1 "$ROUNDS"); do
  python3 tools/voice/pace.py --base "$BASE" --apply --min narration/extent-min.json | tail -3
  node tools/merge.mjs > /dev/null
  node tools/voice/plan.mjs | head -1
  rm -rf "$WORK/proj"; mkdir -p "$WORK/proj"
  tar cf - --exclude=./renders --exclude=./narration/audio --exclude=./narration/review --exclude=./snapshots . | tar xf - -C "$WORK/proj"
  (cd "$WORK/proj" && node tools/mkindex.mjs > /dev/null && node tools/voice/extent.mjs --dir "$PWD" --out "$WORK/extent.json")
  OUT=$(python3 tools/voice/extent_need.py "$WORK/extent.json" narration/extent-min.json)
  echo "round $i: $OUT"
  case "$OUT" in "0 scene(s) raised"*) echo "pictures all fit"; break;; esac
done
