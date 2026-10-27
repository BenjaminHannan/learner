#!/bin/bash
# Merge 138l -- every registered command, in order, one heavy suite at a
# time, `uptime` checked before each step (waits while 1-min load > 60).
# usage: scripts/claude_138l_runall.sh <run_dir> <py-wrapper>
#   <py-wrapper> = the rules' python command
#   (OMP/MKL=1; uv run --offline --no-project --python 3.12 --with torch
#   --with numpy python -B "$@")
set -u
R=$1
PY=$2
cd "$(dirname "$0")/.."
AK=scripts/claude_loop138k_agent.py
CK=artifacts/claude-merge138k-20260922/loop138k-config.json
AL=scripts/claude_loop138l_agent.py
CL=artifacts/claude-merge138l-20260922/loop138l-config.json
PRED=artifacts/claude-merge138l-20260922/predicted_moves138l.json
V=artifacts/claude-verify-20260922/138j
KB=artifacts/claude-merge138k-20260922/run/sd
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
# L1 -- each piece's own cases on own / 138k / 138l
waitload L1
for p in 209 212 216 222 223 226; do for a in own k l; do
  $PY scripts/claude_138l_l1.py run --piece $p --arm $a \
    --out $R/l1/l1-$p-$a.json --work $W/l1-$p-$a > $R/l1-log-$p-$a.txt 2>&1 \
    || echo "ERR L1 $p $a" | tee -a $R/errors.txt
done; done
$PY scripts/claude_138l_l1.py judge --dir $R/l1 --pred $PRED > $R/l1-judge.txt 2>&1
# L2 -- frozen suites vs 138k's saved rows
waitload L2-suites
$PY scripts/fable_suitediff218.py --agent $AL --config $CL --base-dir $KB \
  --out $R/sd --only sessions152,bench,marks123 > $R/sd.log 2>&1
# rt136: suitediff needs sealed redteam136-*.json base rows, which 138k's
# run/sd does not hold, so labels come from 138j's sealed rows (138k K3:
# 0 rt136 moves vs 138j); the scorer ALSO compares every 138l row directly
# with 138k's saved run/sd/rt136-rows.json.
waitload L2-rt136
$PY scripts/fable_suitediff218.py --agent $AL --config $CL \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload L2-rt143
$PY scripts/claude_138l_rt143nogate.py $AL $CL $R/rt143nogate-l.json > $R/rt143nogate.log 2>&1
# L3 -- sleep smoke, same as 138k
for a in k l; do
  waitload L3-$a
  if [ $a = k ]; then AG=$AK; CF=$CK; else AG=$AL; CF=$CL; fi
  $PY scripts/fable_sleepsmoke206.py --agent $AG --config $CF --root $W/smoke-$a \
    --report $R/smoke-$a.json --label $a --idle-seconds 5.0 > $R/smoke-$a.log 2>&1
done
# L4 -- 3 back-to-back bench reruns
for i in 1 2 3; do
  waitload L4-$i
  $PY scripts/fable_suitediff218.py --agent $AL --config $CL --base-dir $KB \
    --out $R/bench$i --only bench > $R/bench$i.log 2>&1
done
# L5 -- latency, alternating processes k,l,k,l,k,l, 2 reps each
for i in 1 2 3; do for a in k l; do
  waitload L5-$a-$i
  if [ $a = k ]; then AG=$AK; CF=$CK; else AG=$AL; CF=$CL; fi
  $PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$a-$i 2 $R/lat-$a-$i.json \
    $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json > $R/lat-$a-$i.log 2>&1
done; done
# L6 -- verifier's 15 dialogs on 138k and 138l
for a in k l; do
  if [ $a = k ]; then AG=$AK; CF=$CK; else AG=$AL; CF=$CL; fi
  $PY scripts/claude_merge138k_probe.py $AG $CF $W/probe-$a $V/p3-dialogs.json \
    $R/probe/$a-p3-dialogs.json > $R/probe/$a-p3-dialogs.txt 2>&1
done
$PY scripts/claude_138l_score.py $R $PRED $R/score138l.json > $R/score.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/l1-judge.txt $R/score.txt
