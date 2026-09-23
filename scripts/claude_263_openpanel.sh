#!/bin/bash
# Exp 263 -- M2: openpanel260 run once on 263 (regression check), then score
# against 260's sealed figures. The panel is run only here, once, on 263.
# usage: scripts/claude_263_openpanel.sh <run_dir>
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
P=artifacts/claude-openpanel260-20260922
PRED=artifacts/claude-comma263-20260923/predicted_moves263.json
mkdir -p "$R" "$R/work"
( cd . && shasum -a 256 -c $P/SEAL.sha256.txt ) > $R/openpanel-seal-check.txt 2>&1 || { cat $R/openpanel-seal-check.txt; echo "OPENPANEL SEAL CHECK FAILED"; exit 4; }
T0=$(date +%s)
PY scripts/claude_comma263_run.py panel scripts/claude_loop263_agent.py \
  artifacts/claude-comma263-20260923/loop263-config.json $R/work/n \
  $P/panel.jsonl $R/openpanel263.jsonl > $R/openpanel263.log 2>&1
PY scripts/claude_comma263_regscore.py $R $PRED $R/openpanel-score263.json M2 > $R/openpanel-score.txt 2>&1
echo "exit $?" >> $R/openpanel-score.txt
echo "TOTAL $(( $(date +%s) - T0 )) s" >> $R/openpanel-score.txt
cat $R/openpanel-score.txt
