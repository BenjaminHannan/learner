#!/bin/bash
# Exp 255b -- registered runs M2, M4, M5, M6, M7, in order, one heavy suite at
# a time, `uptime` checked before each step (waits while 1-min load > 60).
# 138m (base) and 255b are run in the same session wherever a comparison
# needs it. usage: scripts/claude_255b_runall.sh <run_dir> <work_dir>
set -u
R=$1; W=$2
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
AM=scripts/claude_loop138m_agent.py
CM=artifacts/claude-merge138m-20260922/loop138m-config.json
AN=scripts/claude_loop255b_agent.py
CN=artifacts/claude-fixedtext255b-20260923/loop255b-config.json
D=artifacts/claude-fixedtext255b-20260923
PRED=$D/predicted_moves255b.json
V=artifacts/claude-verify-20260922/138j
VK=artifacts/claude-verify-20260922/138k
VM=artifacts/claude-verify-20260922/138m
mkdir -p "$R" "$W" "$R/probe" "$R/vp"
waitload() {
  while :; do
    L=$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
    echo "$(date +%T) uptime load1=$L before: $1" | tee -a "$R/uptime.log"
    awk -v l="$L" 'BEGIN{exit !(l<=60)}' && break
    sleep 30
  done
}
T0=$(date +%s)
# M2 -- frozen suites vs 138m's rows (base138m-rows), then rt143 no-gate
waitload M2-suites
PY scripts/fable_suitediff218.py --agent $AN --config $CN --base-dir $D/base138m-rows \
  --out $R/sd255b --only rt136,rt143,sessions152,bench > $R/sd255b.log 2>&1
waitload M2-rt143nogate
PY scripts/claude_138l_rt143nogate.py $AN $CN $R/rt143nogate-255b.json > $R/rt143nogate.log 2>&1
# M4 -- verifier probes, 138m and 255b, same session
for a in m 255b; do
  if [ $a = m ]; then AG=$AM; CF=$CM; else AG=$AN; CF=$CN; fi
  for p in probes probes-supp; do
    waitload M4-$a-$p
    PY $VM/run_probes.py $AG $CF $W/vp-$a-$p $VM/$p.json $R/vp/$a-$p.json \
      > $R/vp/$a-$p.txt 2>&1
  done
done
# M5 -- sleep smoke on 255b (compared with 138m's saved smoke-m.json)
waitload M5
PY scripts/fable_sleepsmoke206.py --agent $AN --config $CN --root $W/smoke-255b \
  --report $R/smoke-255b.json --label 255b --idle-seconds 5.0 > $R/smoke-255b.log 2>&1
# M6 -- restart and verifier dialogs, 138m and 255b, same session
for a in m 255b; do
  waitload M6-$a
  if [ $a = m ]; then AG=$AM; CF=$CM; else AG=$AN; CF=$CN; fi
  for p in $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json \
           $VK/v-dialogs.json $VK/v-supp.json; do
    b=$(basename $p .json)
    PY scripts/claude_merge138k_probe.py $AG $CF $W/probe-$a-$b $p \
      $R/probe/$a-$b.json > $R/probe/$a-$b.txt 2>&1
  done
done
# M7 -- latency, alternating processes m,255b x3, 2 reps each
for i in 1 2 3; do for a in m 255b; do
  waitload M7-$a-$i
  if [ $a = m ]; then AG=$AM; CF=$CM; else AG=$AN; CF=$CN; fi
  PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$a-$i 2 $R/lat-$a-$i.json \
    $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json > $R/lat-$a-$i.log 2>&1
done; done
if [ "${PREDICT:-0}" = 1 ]; then
  PY scripts/claude_255b_m2check.py $D/base138m-rows $R/sd255b $R/m2-check.json > $R/m2-check.txt 2>&1
  PY scripts/claude_255b_m2check.py --nogate artifacts/claude-merge138m-20260922/run/rt143nogate-m.json \
    $R/rt143nogate-255b.json $R/m2-nogate-check.json >> $R/m2-check.txt 2>&1
  PY scripts/claude_255b_score.py --predict $R $R/predicted_moves255b.json
  PRED=$R/predicted_moves255b.json
fi
PY scripts/claude_255b_score.py $R $PRED $R/score255b.json > $R/score.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/score.txt
