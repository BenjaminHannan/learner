#!/bin/bash
# EXP mut-0 -- F1 run-all with fail-closed SLEEP + sleep smoke.
# Copy of scripts/claude_f1_runall.sh (same agent, config, NEW-1 bench
# path, mouth logging, base rows, scorer) PLUS: mut0 SLEEP suite (must
# report NOT-RUN, fail-closed), fable_sleepsmoke206.py to completion,
# and a combined mut0-verdict.json (overall NEVER PASS while SLEEP is
# NOT-RUN).
# usage: scripts/claude_f1_runall_mut0.sh <run_dir>
# joinpanel292t (regression only), convbench-f0, and the M5 wall run
# separately and are untouched by this task (never re-run here).
# CPU only, at most 4 parallel processes.
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
# splits only -- declared in the F1 PASSMARKS with the S1 anchor (721/721
# agree on 292t's saved conflict replies). sessions152 path is untouched.
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
# MUT0 -- fail-closed SLEEP suite (must exit nonzero with NOT-RUN)
waitload MUT0-sleep
PY scripts/claude_marks_mut0.py --agent $AN --config $CN --out $R/mut0 --suite sleep > $R/mut0-sleep.log 2>&1
echo "mut0 sleep exit $? (expect 2 = NOT-RUN fail-closed)" | tee -a $R/uptime.log
# SMOKE -- live sleep world to completion on this arm
waitload SMOKE-f1
PY scripts/fable_sleepsmoke206.py --agent $AN --config $CN --root $R/smoke206 --report $R/smoke206-f1.json --label sf1 > $R/smoke206.log 2>&1
echo "smoke exit $?" | tee -a $R/uptime.log
# Combined fail-closed verdict (never PASS while SLEEP is NOT-RUN)
PY scripts/claude_marks_mut0.py --runall-verdict --run-dir $R --regscore $R/regscoref1.json --smoke $R/smoke206-f1.json --sleep-out $R/mut0 --agent f1 --out $R/mut0-verdict.json > $R/mut0-verdict.log 2>&1
echo "mut0 verdict exit $? (expect 2 = NOT-RUN)" | tee -a $R/uptime.log
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/regscore.txt
cat $R/mut0-verdict.log
