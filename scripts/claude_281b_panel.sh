#!/bin/bash
# Exp 281b -- M1: the blind calledpanel281b on both arms (281 and 281b).
# usage: scripts/claude_281b_panel.sh <run_dir>
# Schema gate: scripts/claude_called281b_panelrun.py and
# scripts/claude_called281b_panelscore.py check the writer's per-turn schema
# {dialog_id, turn_index, user_text, category, gold} (the runner also
# accepts the key `user` for the text) before scoring anything;
# SCHEMA-MISMATCH exit 3 = VOID, never scored by hand.
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
P=artifacts/claude-calledpanel281b-20260923
mkdir -p "$R" "$R/work"
( cd . && shasum -a 256 -c $P/SEAL.sha256.txt ) > $R/panel-seal-check.txt 2>&1 || { cat $R/panel-seal-check.txt; echo "PANEL SEAL CHECK FAILED"; exit 4; }
ls $P > $R/panel-files.txt 2>&1
cat $R/panel-seal-check.txt
PANEL=$(ls $P/panel.jsonl 2>/dev/null | head -1)
[ -n "$PANEL" ] || { echo "NO PANEL FILE"; exit 5; }
echo "panel file: $PANEL"
T0=$(date +%s)
PY scripts/claude_called281b_panelrun.py panelrun scripts/claude_loop281_agent.py \
  artifacts/claude-called281-20260923/loop281-config.json $R/work/p281b \
  $PANEL $R/panel-281.json > $R/panel-281.log 2>&1 || { cat $R/panel-281.log; echo "PANELRUN 281 FAILED"; exit 6; }
PY scripts/claude_called281b_panelrun.py panelrun scripts/claude_loop281b_agent.py \
  artifacts/claude-called281b-20260923/loop281b-config.json $R/work/n281b \
  $PANEL $R/panel-281b.json > $R/panel-281b.log 2>&1 || { cat $R/panel-281b.log; echo "PANELRUN 281b FAILED"; exit 6; }
PY scripts/claude_called281b_panelscore.py $PANEL $R/panel-281.json \
  $R/panel-281b.json $R/panel-score281b.json > $R/panel-score.txt 2>&1
echo "exit $?" >> $R/panel-score.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" >> $R/panel-score.txt
cat $R/panel-score.txt
