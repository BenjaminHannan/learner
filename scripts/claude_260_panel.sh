#!/bin/bash
# Exp 260 -- M1: the blind openpanel260 on both arms (138m and 260), then score.
# usage: scripts/claude_260_panel.sh <run_dir>
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
P=artifacts/claude-openpanel260-20260922
mkdir -p "$R" "$R/work"
( cd . && shasum -a 256 -c $P/SEAL.sha256.txt ) > $R/panel-seal-check.txt 2>&1 || { cat $R/panel-seal-check.txt; echo "PANEL SEAL CHECK FAILED"; exit 4; }
PY scripts/claude_openers260_score.py schema $P > $R/panel-schema.txt 2>&1
SC=$?; cat $R/panel-schema.txt
[ $SC -eq 0 ] || { echo "schema check exit $SC: run VOID"; exit $SC; }
T0=$(date +%s)
PY scripts/claude_openers260_run.py panel scripts/claude_loop138m_agent.py \
  artifacts/claude-merge138m-20260922/loop138m-config.json $R/work/m \
  $P/panel.jsonl $R/panel-138m.jsonl > $R/panel-138m.log 2>&1
PY scripts/claude_openers260_run.py panel scripts/claude_loop260_agent.py \
  artifacts/claude-openers260-20260922/loop260-config.json $R/work/n \
  $P/panel.jsonl $R/panel-260.jsonl > $R/panel-260.log 2>&1
PY scripts/claude_openers260_score.py panel $P $R/panel-260.jsonl \
  $R/panel-138m.jsonl $R/panel-score260.json > $R/panel-score.txt 2>&1
echo "exit $?" >> $R/panel-score.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" >> $R/panel-score.txt
cat $R/panel-score.txt
