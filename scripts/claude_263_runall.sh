#!/bin/bash
# Exp 263 -- registered marks M3 (suites), PROBES, M4 (latency), in order,
# one heavy step at a time, `uptime` checked before each step
# (waits while 1-min load > 60).
# usage: scripts/claude_263_runall.sh <run_dir>
# M1 (blind commapanel263) runs separately: scripts/claude_263_panel.sh
# M2 (openpanel260 regression) runs separately: scripts/claude_263_openpanel.sh
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
A0=scripts/claude_loop260_agent.py
C0=artifacts/claude-openers260-20260922/loop260-config.json
AN=scripts/claude_loop263_agent.py
CN=artifacts/claude-comma263-20260923/loop263-config.json
PRED=artifacts/claude-comma263-20260923/predicted_moves263.json
V=artifacts/claude-verify-20260922/138j
VM=artifacts/claude-verify-20260922/138m
MB=artifacts/claude-merge138m-20260922/run/sd
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
# M3 -- frozen suites, same commands and bases as 260's runall
waitload M3-suites
PY scripts/fable_suitediff218.py --agent $AN --config $CN --base-dir $MB \
  --out $R/sd --only sessions152,bench > $R/sd.log 2>&1
waitload M3-rt136
PY scripts/fable_suitediff218.py --agent $AN --config $CN \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M3-rt143
PY scripts/claude_138l_rt143nogate.py $AN $CN $R/rt143nogate-n.json > $R/rt143nogate.log 2>&1
# PROBES -- 138m verifier probes on 263 (vs 138m's saved rows)
waitload PROBES
PY $VM/run_probes.py $AN $CN $W/vp-n $VM/probes.json $R/vp-n.json > $R/vp-n.log 2>&1
PY $VM/run_probes.py $AN $CN $W/vs-n $VM/probes-supp.json $R/vs-n.json > $R/vs-n.log 2>&1
# M4 -- latency, alternating processes 260,263 x3 in the same session
for i in 1 2 3; do for a in 260 263; do
  waitload M4-$a-$i
  if [ $a = 260 ]; then AG=$A0; CF=$C0; else AG=$AN; CF=$CN; fi
  PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$a-$i 2 $R/lat-$a-$i.json \
    $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json > $R/lat-$a-$i.log 2>&1
done; done
PY scripts/claude_comma263_regscore.py $R $PRED $R/regscore263.json > $R/regscore.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/regscore.txt
