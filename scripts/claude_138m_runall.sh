#!/bin/bash
# Merge 138m -- every registered command, in order, one heavy suite at a
# time, `uptime` checked before each step (waits while 1-min load > 60).
# usage: scripts/claude_138m_runall.sh <run_dir>
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
AL=scripts/claude_loop138l_agent.py
CL=artifacts/claude-merge138l-20260922/loop138l-config.json
AM=scripts/claude_loop138m_agent.py
CM=artifacts/claude-merge138m-20260922/loop138m-config.json
PRED=artifacts/claude-merge138m-20260922/predicted_moves138m.json
V=artifacts/claude-verify-20260922/138j
VK=artifacts/claude-verify-20260922/138k
LB=artifacts/claude-merge138l-20260922/run/sd
W=$R/work
mkdir -p "$R" "$W" "$R/l1" "$R/probe"
waitload() {
  while :; do
    L=$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
    echo "$(date +%T) uptime load1=$L before: $1" | tee -a "$R/uptime.log"
    awk -v l="$L" 'BEGIN{exit !(l<=60)}' && break
    sleep 30
  done
}
T0=$(date +%s)
# M1 -- each piece's own sealed dev cases on own / line head / 138l / 138m
for a in own head l m; do
  waitload M1-$a
  PY scripts/claude_138m_l1.py run --arm $a --out-dir $R/l1 --work $W/l1-$a \
    > $R/l1-log-$a.txt 2>&1 || echo "ERR M1 $a" | tee -a $R/errors.txt
done
PY scripts/claude_138m_l1.py sealed --dir $R/l1 --out $R/l1-sealed.json > $R/l1-sealed.txt 2>&1
PY scripts/claude_138m_l1.py judge --dir $R/l1 --pred $PRED --out $R/l1-judge.json > $R/l1-judge.txt 2>&1
# M2 -- frozen suites vs 138l's saved rows
waitload M2-suites
PY scripts/fable_suitediff218.py --agent $AM --config $CM --base-dir $LB \
  --out $R/sd --only sessions152,bench,marks123 > $R/sd.log 2>&1
# rt136 labels vs 138j's sealed rows (same method as 138l); the scorer also
# compares every row directly with 138l's saved run/sd136/rt136-rows.json.
waitload M2-rt136
PY scripts/fable_suitediff218.py --agent $AM --config $CM \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M2-rt143
PY scripts/claude_138l_rt143nogate.py $AM $CM $R/rt143nogate-m.json > $R/rt143nogate.log 2>&1
# M3 -- sleep smoke on 138l and 138m
for a in l m; do
  waitload M3-$a
  if [ $a = l ]; then AG=$AL; CF=$CL; else AG=$AM; CF=$CM; fi
  PY scripts/fable_sleepsmoke206.py --agent $AG --config $CF --root $W/smoke-$a \
    --report $R/smoke-$a.json --label $a --idle-seconds 5.0 > $R/smoke-$a.log 2>&1
done
# M4 -- 3 back-to-back bench reruns on 138m
for i in 1 2 3; do
  waitload M4-$i
  PY scripts/fable_suitediff218.py --agent $AM --config $CM --base-dir $LB \
    --out $R/bench$i --only bench > $R/bench$i.log 2>&1
done
# M5 -- latency, alternating processes l,m,l,m,l,m, 2 reps each
for i in 1 2 3; do for a in l m; do
  waitload M5-$a-$i
  if [ $a = l ]; then AG=$AL; CF=$CL; else AG=$AM; CF=$CM; fi
  PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$a-$i 2 $R/lat-$a-$i.json \
    $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json > $R/lat-$a-$i.log 2>&1
done; done
# M6 -- restart and verifier dialogs (138j p3 set + 138k v-dialogs/v-supp)
for a in l m; do
  waitload M6-$a
  if [ $a = l ]; then AG=$AL; CF=$CL; else AG=$AM; CF=$CM; fi
  for p in $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json \
           $VK/v-dialogs.json $VK/v-supp.json; do
    b=$(basename $p .json)
    PY scripts/claude_merge138k_probe.py $AG $CF $W/probe-$a-$b $p \
      $R/probe/$a-$b.json > $R/probe/$a-$b.txt 2>&1
  done
done
PY scripts/claude_138m_score.py $R $PRED $R/score138m.json > $R/score.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/l1-sealed.txt $R/l1-judge.txt $R/score.txt
