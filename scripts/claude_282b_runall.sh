#!/bin/bash
# Exp 282b -- registered marks M2 (+ verifier probes), in order, one heavy
# step at a time, `uptime` checked before each step (waits while 1-min
# load > 60).
# usage: scripts/claude_282b_runall.sh <run_dir>
# M1 (the blind panel) and M3 (smalltalkpanel234 rerun) run separately:
# scripts/claude_282b_panelrun.sh <run_dir>
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
AN=scripts/claude_loop282b_agent.py
CN=artifacts/claude-small282b-20260923/loop282b-config.json
B282=artifacts/claude-small282-20260923/run
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
}
T0=$(date +%s)
# M2 -- frozen suites vs 282's saved rows (base-dir = 282's run dirs)
waitload M2-suites
PY scripts/fable_suitediff218.py --agent $AN --config $CN --base-dir $B282/sd \
  --out $R/sd --only sessions152,bench > $R/sd.log 2>&1
waitload M2-rt136
PY scripts/fable_suitediff218.py --agent $AN --config $CN \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M2-rt143
PY scripts/claude_138l_rt143nogate.py $AN $CN $R/rt143nogate-282b.json > $R/rt143nogate.log 2>&1
# Verifier probes (vs 282's saved rows vp-282.json / vs-282.json)
waitload VP
PY $VM/run_probes.py $AN $CN $W/vp-282b $VM/probes.json $R/vp-282b.json > $R/vp-282b.log 2>&1
PY $VM/run_probes.py $AN $CN $W/vs-282b $VM/probes-supp.json $R/vs-282b.json > $R/vs-282b.log 2>&1
PY scripts/claude_small282b_regscore.py $R $R/regscore282b.json > $R/regscore.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/regscore.txt
