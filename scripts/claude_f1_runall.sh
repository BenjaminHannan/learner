#!/bin/bash
# Exp F1 -- registered marks M2 (+ verifier probes), in order, one heavy
# step at a time, `uptime` checked before each step (waits while 1-min
# load > 60, stops under 3 GB free).
# usage: scripts/claude_f1_runall.sh <run_dir>
# Base rows are 292t's sealed registered rows
# (artifacts/claude-join292t-20260923/run): F1 must differ from 292t only
# by 241b reply rewrites (GATE identical to 292t's).
# joinpanel292t (regression only), convbench-f0, and the M5 wall run
# separately. CPU only, at most 4 parallel processes.
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export MOUTH241B_LOG=
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
AN=scripts/claude_loopf1_agent.py
CN=artifacts/claude-f1-20260923/loopf1-config.json
B292T=artifacts/claude-join292t-20260923/run
VM=artifacts/claude-verify-20260922/138m
W=$R/work
mkdir -p "$R" "$W"
# Behavior-neutral mouth logging for M2b evidence (every rewritten line).
export MOUTH241B_LOG="$R/mouthf1.jsonl"
: > "$MOUTH241B_LOG"
waitload() {
  while :; do
    L=$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
    echo "$(date +%T) uptime load1=$L before: $1" | tee -a "$R/uptime.log"
    awk -v l="$L" 'BEGIN{exit !(l<=60)}' && break
    sleep 30
  done
  F=$(df -g / | tail -1 | awk '{print $4}')
  if [ "$F" -lt 3 ]; then echo "free disk ${F} GB < 3: STOP"; exit 5; fi
}
T0=$(date +%s)
# M2 -- frozen suites vs 292t's saved rows.
# sessions152+bench run through scripts/claude_f1_suites.py, which swaps in
# 241b's sealed NEW-1 confirm (claude_fix172b241b_benchv3) for the v3 bench
# splits only -- declared in PASSMARKS with the S1 anchor (721/721 agree on
# 292t's saved conflict replies). sessions152 path is untouched by the swap.
waitload M2-suites
PY scripts/claude_f1_suites.py -- --agent $AN --config $CN --base-dir $B292T/sd \
  --out $R/sd --only sessions152,bench > $R/sd.log 2>&1
waitload M2-rt136
PY scripts/fable_suitediff218.py --agent $AN --config $CN \
  --base-dir $B292T/sd136 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M2-rt143
PY scripts/claude_138l_rt143nogate.py $AN $CN $R/rt143nogate-f1.json > $R/rt143nogate.log 2>&1
# Verifier probes (vs 292t's saved rows vp-292t.json / vs-292t.json)
waitload VP
PY $VM/run_probes.py $AN $CN $W/vp-f1 $VM/probes.json $R/vp-f1.json > $R/vp-f1.log 2>&1
PY $VM/run_probes.py $AN $CN $W/vs-f1 $VM/probes-supp.json $R/vs-f1.json > $R/vs-f1.log 2>&1
PY scripts/claude_f1_regscore.py $R $R/regscoref1.json > $R/regscore.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/regscore.txt
