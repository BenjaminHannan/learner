#!/bin/bash
# Exp 258 M1: blind panel corrtail258, run ONCE on both arms, then scored.
# Run from the repo root only after artifacts/claude-corrtail258-20260922/
# SEAL.sha256.txt exists and `shasum -a 256 -c` on it is OK.
set -u
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
D=artifacts/claude-comment258-20260922
R=$D/run
P=artifacts/claude-corrtail258-20260922
B=artifacts/claude-correct252b-20260922
W=${TMPDIR:-/tmp}/claude258-work
mkdir -p $R $W
shasum -a 256 -c $P/SEAL.sha256.txt > $R/m1-seal-check.txt 2>&1 || { echo "panel SEAL check failed"; cat $R/m1-seal-check.txt; exit 4; }
uptime; df -g / | tail -1
$PY scripts/claude_corr252_run.py --agent scripts/claude_loop252b_agent.py --config $B/loop252b-config.json --cases $P/panel.jsonl --work $W/m1b --out $R/corrtail258-252b.jsonl > $R/corrtail258-252b.log 2>&1
$PY scripts/claude_corr252_run.py --agent scripts/claude_loop258_agent.py --config $D/loop258-config.json --cases $P/panel.jsonl --work $W/m1m --out $R/corrtail258-258.jsonl > $R/corrtail258-258.log 2>&1
python3 scripts/claude_comment258_score.py panel $P $R/corrtail258-258.jsonl $R/corrtail258-252b.jsonl > $R/m1-score.txt
echo "score exit=$?" >> $R/m1-score.txt
