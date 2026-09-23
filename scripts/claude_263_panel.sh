#!/bin/bash
# Exp 263 -- M1: the blind commapanel263 on both arms (260 and 263), then score.
# usage: scripts/claude_263_panel.sh <run_dir>
# The panel folder is never opened before the seal; this script runs only
# after artifacts/claude-commapanel263-20260923/SEAL.sha256.txt exists and
# checks OK from the repo root. Each arm runs the panel exactly once.
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
P=artifacts/claude-commapanel263-20260923
mkdir -p "$R" "$R/work"
( cd . && shasum -a 256 -c $P/SEAL.sha256.txt ) > $R/panel-seal-check.txt 2>&1 || { cat $R/panel-seal-check.txt; echo "PANEL SEAL CHECK FAILED"; exit 4; }
PY scripts/claude_comma263_score.py schema $P > $R/panel-schema.txt 2>&1
SC=$?; cat $R/panel-schema.txt
[ $SC -eq 0 ] || { echo "schema check exit $SC: run VOID"; exit $SC; }
T0=$(date +%s)
PY scripts/claude_comma263_run.py panel scripts/claude_loop260_agent.py \
  artifacts/claude-openers260-20260922/loop260-config.json $R/work/m \
  $P/panel.jsonl $R/commapanel-260.jsonl > $R/commapanel-260.log 2>&1
PY scripts/claude_comma263_run.py panel scripts/claude_loop263_agent.py \
  artifacts/claude-comma263-20260923/loop263-config.json $R/work/n \
  $P/panel.jsonl $R/commapanel-263.jsonl > $R/commapanel-263.log 2>&1
PY scripts/claude_comma263_score.py panel $P $R/commapanel-263.jsonl \
  $R/commapanel-260.jsonl $R/commapanel-score263.json > $R/commapanel-score.txt 2>&1
echo "exit $?" >> $R/commapanel-score.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" >> $R/commapanel-score.txt
cat $R/commapanel-score.txt
