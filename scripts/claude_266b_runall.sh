#!/bin/bash
# Exp 266b -- every registered command, in order, one heavy suite at a time,
# `uptime` checked before each step (waits while 1-min load > 60).
# usage: scripts/claude_266b_runall.sh <run_dir>
# M2/M3 compare 266b against 266's saved rows
# (artifacts/claude-chain266-20260923/run); M4 alternates 266 (m) and 266b (n).
# Mirrors scripts/claude_266_runall.sh one-for-one.
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
AM=scripts/claude_loop266_agent.py
CM=artifacts/claude-chain266-20260923/loop266-config.json
AN=scripts/claude_loop266b_agent.py
CN=artifacts/claude-chain266b-20260923/loop266b-config.json
PRED=artifacts/claude-chain266b-20260923/predicted_moves266b.json
MB=artifacts/claude-chain266-20260923/run
V=artifacts/claude-verify-20260922/138j
VK=artifacts/claude-verify-20260922/138k
VM=artifacts/claude-verify-20260922/138m
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
# M2 -- frozen suites vs 266's saved rows
waitload M2-suites
PY scripts/fable_suitediff218.py --agent $AN --config $CN --base-dir $MB/sd \
  --out $R/sd --only sessions152,bench,marks123 > $R/sd.log 2>&1
waitload M2-rt136
PY scripts/fable_suitediff218.py --agent $AN --config $CN \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M2-rt143
PY scripts/claude_138l_rt143nogate.py $AN $CN $R/rt143nogate-n.json > $R/rt143nogate.log 2>&1
# M3a -- restart and verifier dialogs (138j p3 set + 138k v-dialogs/v-supp)
for p in $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json \
         $VK/v-dialogs.json $VK/v-supp.json; do
  b=$(basename $p .json)
  waitload M3a-$b
  PY scripts/claude_merge138k_probe.py $AN $CN $W/probe-n-$b $p \
    $R/probe/n-$b.json > $R/probe/n-$b.txt 2>&1
done
# M3b -- 138m verifier probes (probes.json + probes-supp.json)
for p in probes probes-supp; do
  waitload M3b-$p
  case $p in probes) o=probe266b.json;; probes-supp) o=probe266b-supp.json;; esac
  PY artifacts/claude-verify-20260922/138m/run_probes.py $AN $CN $W/probe266b-$p \
    $VM/$p.json $R/$o > $R/probe266b-$p.log 2>&1
done
# M4 -- latency, alternating processes m(266),n(266b),m,n,m,n, 2 reps each
for i in 1 2 3; do for a in m n; do
  waitload M4-$a-$i
  if [ $a = m ]; then AG=$AM; CF=$CM; else AG=$AN; CF=$CN; fi
  PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$a-$i 2 $R/lat-$a-$i.json \
    $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json > $R/lat-$a-$i.log 2>&1
done; done
PY scripts/claude_266b_score.py $R $PRED $R/score266b.json > $R/score.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a "$R/uptime.log"
cat $R/score.txt
