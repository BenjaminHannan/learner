#!/bin/bash
# Exp 260 -- registered marks M2-M6, in order, one heavy step at a time,
# `uptime` checked before each step (waits while 1-min load > 60).
# usage: scripts/claude_260_runall.sh <run_dir>
# M1 (the blind panel) runs separately: scripts/claude_260_panel.sh <run_dir>
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
AM=scripts/claude_loop138m_agent.py
CM=artifacts/claude-merge138m-20260922/loop138m-config.json
AN=scripts/claude_loop260_agent.py
CN=artifacts/claude-openers260-20260922/loop260-config.json
PRED=artifacts/claude-openers260-20260922/predicted_moves260.json
V=artifacts/claude-verify-20260922/138j
VK=artifacts/claude-verify-20260922/138k
VM=artifacts/claude-verify-20260922/138m
MB=artifacts/claude-merge138m-20260922/run/sd
W=$R/work
mkdir -p "$R" "$W" "$R/probe"
waitload() {
  while :; do
    L=$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
    echo "$(date +%T) uptime load1=$L before: $1" | tee -a "$R/uptime.log"
    awk -v l="$L" 'BEGIN{exit !(l<=60)}' && break
    sleep 30
  done
}
T0=$(date +%s)
# M2 -- frozen suites; rows compared directly with 138m's saved rows
waitload M2-suites
PY scripts/fable_suitediff218.py --agent $AN --config $CN --base-dir $MB \
  --out $R/sd --only sessions152,bench > $R/sd.log 2>&1
waitload M2-rt136
PY scripts/fable_suitediff218.py --agent $AN --config $CN \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M2-rt143
PY scripts/claude_138l_rt143nogate.py $AN $CN $R/rt143nogate-n.json > $R/rt143nogate.log 2>&1
# M3 -- sleep smoke on 260 (vs 138m's saved smoke-m.json)
waitload M3
PY scripts/fable_sleepsmoke206.py --agent $AN --config $CN --root $W/smoke-n \
  --report $R/smoke-n.json --label n --idle-seconds 5.0 > $R/smoke-n.log 2>&1
# M4 -- 138m verifier probes (vs 138m's saved rows)
waitload M4
PY $VM/run_probes.py $AN $CN $W/vp-n $VM/probes.json $R/vp-n.json > $R/vp-n.log 2>&1
PY $VM/run_probes.py $AN $CN $W/vs-n $VM/probes-supp.json $R/vs-n.json > $R/vs-n.log 2>&1
# M5 -- restart dialogs (138m's M6 files; vs 138m's saved probe rows)
waitload M5
for p in $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json \
         $VK/v-dialogs.json $VK/v-supp.json; do
  b=$(basename $p .json)
  PY scripts/claude_merge138k_probe.py $AN $CN $W/probe-n-$b $p \
    $R/probe/n-$b.json > $R/probe/n-$b.txt 2>&1
done
# M6 -- latency, alternating processes m,n,m,n,m,n, 2 reps each
for i in 1 2 3; do for a in m n; do
  waitload M6-$a-$i
  if [ $a = m ]; then AG=$AM; CF=$CM; else AG=$AN; CF=$CN; fi
  PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$a-$i 2 $R/lat-$a-$i.json \
    $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json > $R/lat-$a-$i.log 2>&1
done; done
PY scripts/claude_openers260_regscore.py $R $PRED $R/regscore260.json > $R/regscore.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/regscore.txt
