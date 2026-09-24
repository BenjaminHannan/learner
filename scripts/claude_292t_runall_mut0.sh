#!/bin/bash
# EXP mut-0 -- 292t run-all with fail-closed SLEEP + sleep smoke.
# Copy of scripts/claude_292t_runall.sh (same agent, config, base rows,
# steps, scorer) PLUS: mut0 SLEEP suite (must report NOT-RUN, fail-closed),
# fable_sleepsmoke206.py to completion, and a combined mut0-verdict.json
# (overall NEVER PASS while SLEEP is NOT-RUN).
# usage: scripts/claude_292t_runall_mut0.sh <run_dir>
# M1 (blind join panel) and M3 (smalltalkpanel234) run separately and are
# untouched by this task (never re-run here).
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
AN=scripts/claude_loop292t_agent.py
CN=artifacts/claude-join292t-20260923/loop292t-config.json
B292=artifacts/claude-merge292-20260923/run
VM=artifacts/claude-verify-20260922/138m
W=$R/work
mkdir -p "$R" "$W"
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
# M2 -- frozen suites vs 292's saved rows (base-dir = 292's run dirs)
waitload M2-suites
PY scripts/fable_suitediff218.py --agent $AN --config $CN --base-dir $B292/sd \
  --out $R/sd --only sessions152,bench > $R/sd.log 2>&1
waitload M2-rt136
PY scripts/fable_suitediff218.py --agent $AN --config $CN \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M2-rt143
PY scripts/claude_138l_rt143nogate.py $AN $CN $R/rt143nogate-292t.json > $R/rt143nogate.log 2>&1
# Verifier probes (vs 292's saved rows vp-292-probes.json / vp-292-supp.json)
waitload VP
PY $VM/run_probes.py $AN $CN $W/vp-292t $VM/probes.json $R/vp-292t.json > $R/vp-292t.log 2>&1
PY $VM/run_probes.py $AN $CN $W/vs-292t $VM/probes-supp.json $R/vs-292t.json > $R/vs-292t.log 2>&1
PY scripts/claude_292t_regscore.py $R $R/regscore292t.json > $R/regscore.txt 2>&1
# MUT0 -- fail-closed SLEEP suite (must exit nonzero with NOT-RUN)
waitload MUT0-sleep
PY scripts/claude_marks_mut0.py --agent $AN --config $CN --out $R/mut0 --suite sleep > $R/mut0-sleep.log 2>&1
echo "mut0 sleep exit $? (expect 2 = NOT-RUN fail-closed)" | tee -a $R/uptime.log
# SMOKE -- live sleep world to completion on this arm
waitload SMOKE-292t
PY scripts/fable_sleepsmoke206.py --agent $AN --config $CN --root $R/smoke206 --report $R/smoke206-292t.json --label s292t > $R/smoke206.log 2>&1
echo "smoke exit $?" | tee -a $R/uptime.log
# Combined fail-closed verdict (never PASS while SLEEP is NOT-RUN)
PY scripts/claude_marks_mut0.py --runall-verdict --run-dir $R --regscore $R/regscore292t.json --smoke $R/smoke206-292t.json --sleep-out $R/mut0 --agent 292t --out $R/mut0-verdict.json > $R/mut0-verdict.log 2>&1
echo "mut0 verdict exit $? (expect 2 = NOT-RUN)" | tee -a $R/uptime.log
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/regscore.txt
cat $R/mut0-verdict.log
