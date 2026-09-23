#!/bin/bash
# Exp 280b -- M1: the blind capabilpanel280b on both arms (280 and 280b).
# usage: scripts/claude_280b_panel.sh <run_dir>
# Schema gate: scripts/claude_capab280b_run.py / score.py require flat
# turn rows with dialog_id, turn_index, user_text (scored turn = last
# row per dialog); violations print SCHEMA-MISMATCH and exit 3 (VOID).
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
P=artifacts/claude-capabilpanel280b-20260923
mkdir -p "$R" "$R/work"
( cd . && shasum -a 256 -c $P/SEAL.sha256.txt ) > $R/panel-seal-check.txt 2>&1 || { cat $R/panel-seal-check.txt; echo "PANEL SEAL CHECK FAILED"; exit 4; }
ls $P > $R/panel-files.txt 2>&1
cat $R/panel-seal-check.txt
PANEL=$(ls $P/panel.jsonl $P/panel.json 2>/dev/null | head -1)
[ -n "$PANEL" ] || { echo "NO PANEL FILE"; exit 5; }
echo "panel file: $PANEL"
T0=$(date +%s)
PY scripts/claude_capab280b_run.py panel scripts/claude_loop280_agent.py \
  artifacts/claude-capab280-20260923/loop280-config.json $R/work/m280b \
  $PANEL $R/panel-280.json > $R/panel-280.log 2>&1
echo "arm280 exit $?" >> $R/panel-280.log
PY scripts/claude_capab280b_run.py panel scripts/claude_loop280b_agent.py \
  artifacts/claude-capab280b-20260923/loop280b-config.json $R/work/n280b \
  $PANEL $R/panel-280b.json > $R/panel-280b.log 2>&1
echo "arm280b exit $?" >> $R/panel-280b.log
PY scripts/claude_capab280b_score.py panel $PANEL $R/panel-280.json \
  $R/panel-280b.json $R/panel-score280b.json > $R/panel-score.txt 2>&1
echo "exit $?" >> $R/panel-score.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" >> $R/panel-score.txt
cat $R/panel-score.txt
