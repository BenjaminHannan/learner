#!/bin/bash
# Exp 282b -- M1: the blind smallpanel282b on both arms (282 and 282b);
# M3: smalltalkpanel234 rerun on both arms (282 and 282b).
# usage: scripts/claude_282b_panelrun.sh <run_dir>
# Strict schema (columns dialog_id, turn_index, user_text, category,
# gold; categories greeting/closing/mixed/control; `user` also accepted
# for the text): scripts/claude_small282b_run.py refuses to run on any
# schema violation or empty turn text, and
# scripts/claude_small282b_score.py gates SCHEMA-MISMATCH (exit 3 = VOID).
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
P=artifacts/claude-smallpanel282b-20260923
S234=artifacts/claude-smalltalkpanel234-20260922
A282=scripts/claude_loop282_agent.py
C282=artifacts/claude-small282-20260923/loop282-config.json
A282B=scripts/claude_loop282b_agent.py
C282B=artifacts/claude-small282b-20260923/loop282b-config.json
mkdir -p "$R" "$R/work"
( cd . && shasum -a 256 -c $P/SEAL.sha256.txt ) > $R/panel-seal-check.txt 2>&1 || { cat $R/panel-seal-check.txt; echo "PANEL SEAL CHECK FAILED"; exit 4; }
ls $P > $R/panel-files.txt 2>&1
cat $R/panel-seal-check.txt
PANEL=$(ls $P/panel.jsonl $P/panel.json 2>/dev/null | head -1)
[ -n "$PANEL" ] || { echo "NO PANEL FILE"; exit 5; }
echo "panel file: $PANEL"
T0=$(date +%s)
PY scripts/claude_small282b_run.py panel $A282 $C282 $R/work/p282b \
  $PANEL $R/panel-282.json $R/probes-282.json > $R/panel-282.log 2>&1
PY scripts/claude_small282b_run.py panel $A282B $C282B $R/work/n282b \
  $PANEL $R/panel-282b.json $R/probes-282b.json > $R/panel-282b.log 2>&1
PY scripts/claude_small282b_score.py panel $PANEL $R/panel-282.json \
  $R/panel-282b.json $R/probes-282.json $R/probes-282b.json $R/panel-score282b.json > $R/panel-score.txt 2>&1
echo "exit $?" >> $R/panel-score.txt
PY scripts/claude_small282b_run.py st234 $A282 $C282 $R/work/s282 \
  $S234/panel.jsonl $R/st234-282.json $R/st234-probes-282.json > $R/st234-282.log 2>&1
PY scripts/claude_small282b_run.py st234 $A282B $C282B $R/work/s282b \
  $S234/panel.jsonl $R/st234-282b.json $R/st234-probes-282b.json > $R/st234-282b.log 2>&1
PY scripts/claude_small282b_score.py st234 $S234/panel.jsonl $R/st234-282.json \
  $R/st234-282b.json $R/st234-probes-282.json $R/st234-probes-282b.json $R/st234-score282b.json >> $R/panel-score.txt 2>&1
echo "exit $?" >> $R/panel-score.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" >> $R/panel-score.txt
cat $R/panel-score.txt
