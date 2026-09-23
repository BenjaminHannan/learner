#!/bin/bash
# Exp 282 -- M1: the blind smallpanel282 on both arms (260 and 282);
# M3: smalltalkpanel234 rerun on both arms (260 and 282).
# usage: scripts/claude_282_panel.sh <run_dir>
# No exact panel schema was given in the brief, so there is no schema
# gate: scripts/claude_small282_run.py loads items flexibly and
# scripts/claude_small282_score.py counts mechanically (ids only).
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
P=artifacts/claude-smallpanel282-20260923
S234=artifacts/claude-smalltalkpanel234-20260922
A260=scripts/claude_loop260_agent.py
C260=artifacts/claude-openers260-20260922/loop260-config.json
A282=scripts/claude_loop282_agent.py
C282=artifacts/claude-small282-20260923/loop282-config.json
mkdir -p "$R" "$R/work"
( cd . && shasum -a 256 -c $P/SEAL.sha256.txt ) > $R/panel-seal-check.txt 2>&1 || { cat $R/panel-seal-check.txt; echo "PANEL SEAL CHECK FAILED"; exit 4; }
ls $P > $R/panel-files.txt 2>&1
cat $R/panel-seal-check.txt
PANEL=$(ls $P/panel.jsonl $P/panel.json 2>/dev/null | head -1)
[ -n "$PANEL" ] || { echo "NO PANEL FILE"; exit 5; }
echo "panel file: $PANEL"
T0=$(date +%s)
PY scripts/claude_small282_run.py panel $A260 $C260 $R/work/p282 \
  $PANEL $R/panel-260.json $R/probes-260.json > $R/panel-260.log 2>&1
PY scripts/claude_small282_run.py panel $A282 $C282 $R/work/n282 \
  $PANEL $R/panel-282.json $R/probes-282.json > $R/panel-282.log 2>&1
PY scripts/claude_small282_score.py panel $PANEL $R/panel-260.json \
  $R/panel-282.json $R/probes-260.json $R/probes-282.json $R/panel-score282.json > $R/panel-score.txt 2>&1
echo "exit $?" >> $R/panel-score.txt
PY scripts/claude_small282_run.py st234 $A260 $C260 $R/work/s260 \
  $S234/panel.jsonl $R/st234-260.json $R/st234-probes-260.json > $R/st234-260.log 2>&1
PY scripts/claude_small282_run.py st234 $A282 $C282 $R/work/s282 \
  $S234/panel.jsonl $R/st234-282.json $R/st234-probes-282.json > $R/st234-282.log 2>&1
PY scripts/claude_small282_score.py st234 $S234/panel.jsonl $R/st234-260.json \
  $R/st234-282.json $R/st234-probes-260.json $R/st234-probes-282.json $R/st234-score282.json >> $R/panel-score.txt 2>&1
echo "exit $?" >> $R/panel-score.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" >> $R/panel-score.txt
cat $R/panel-score.txt
