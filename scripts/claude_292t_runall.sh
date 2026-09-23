#!/bin/bash
# Exp 292t -- registered marks M2 (+ verifier probes), in order, one heavy
# step at a time, `uptime` checked before each step (waits while 1-min
# load > 60, stops under 3 GB free).
# usage: scripts/claude_292t_runall.sh <run_dir>
# M1 (the blind join panel) and M3 (smalltalkpanel234) run separately:
# scripts/claude_292t_panel.sh <run_dir>
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
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/regscore.txt
