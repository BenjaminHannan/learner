#!/bin/bash
# Merge 291 -- registered marks M1-M6, in order, one heavy step at a time,
# `uptime` checked before each step (waits while 1-min load > 60, stops
# under 3 GB free). usage: scripts/claude_291_runall.sh <run_dir>
# M7 (regression panels) runs separately: scripts/claude_291_panel.sh <tmpdir>
# M8 (fresh blind panel) runs separately: scripts/claude_291_m8.sh <tmpdir>
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
SPY() { uv run --offline --no-project --python 3.12 python -B "$@"; }
ANB=scripts/claude_loop138nb_agent.py
CNB=artifacts/claude-merge138nb-20260923/loop138nb-config.json
AP=scripts/claude_loop138p_agent.py
CP=artifacts/claude-merge138p-20260923/loop138p-config.json
A291=scripts/claude_loop291_agent.py
C291=artifacts/claude-join291-20260923/loop291-config.json
PRED=artifacts/claude-join291-20260923/predicted_moves291.json
NBRUN=artifacts/claude-merge138nb-20260923/run
D2=artifacts/claude-correct252b-20260922/dev252b.jsonl
D8=artifacts/claude-comment258-20260922/dev258.jsonl
D9=artifacts/claude-boundary259-20260922/dev259.jsonl
DEV260=artifacts/claude-openers260-20260922/devcases260.json
A260=scripts/claude_loop260_agent.py
C260=artifacts/claude-openers260-20260922/loop260-config.json
A252C=scripts/claude_loop252c_agent.py
C252C=artifacts/claude-merge252c-20260922/loop252c-config.json
V=artifacts/claude-verify-20260922/138j
VK=artifacts/claude-verify-20260922/138k
VM=artifacts/claude-verify-20260922/138m
W=$R/work
mkdir -p "$R" "$W" "$R/m1720" "$R/m1dev" "$R/probe"
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
# M1-720 -- 138nb's sealed dev/case files (720) on nb (own), 138p, 291
for arm in nb p 291; do
  waitload M1-720-$arm
  PY scripts/claude_291_m1.py run --arm $arm --out-dir $R/m1720 --work $W/m1720-$arm \
    > $R/m1720-log-$arm.txt 2>&1 || echo "ERR M1-720 $arm" | tee -a $R/errors.txt
done
PY scripts/claude_291_m1.py judge --dir $R/m1720 --pred $PRED --out $R/m1720-judge.json > $R/m1720-judge.txt 2>&1
# M1B -- 260 devcases on 260 (own), 138p, 291
waitload M1B-260dev
PY scripts/claude_openers260_run.py dev $A260 $C260 $W/dev260-own $DEV260 $R/m1dev/dev260-own.json > $R/m1dev/dev260-own.log 2>&1
PY scripts/claude_openers260_run.py dev $AP $CP $W/dev260-p $DEV260 $R/m1dev/dev260-p.json > $R/m1dev/dev260-p.log 2>&1
PY scripts/claude_openers260_run.py dev $A291 $C291 $W/dev260-291 $DEV260 $R/m1dev/dev260-291.json > $R/m1dev/dev260-291.log 2>&1
# M1C -- 252c devs on 252c (own) and 291
waitload M1C-dev252b
PY scripts/claude_corr252_run.py --agent $A252C --config $C252C --cases $D2 --work $W/dev252b-252c --out $R/m1dev/dev252b-252c.jsonl > $R/m1dev/dev252b-252c.log 2>&1
PY scripts/claude_corr252_run.py --agent $A291 --config $C291 --cases $D2 --work $W/dev252b-291 --out $R/m1dev/dev252b-291.jsonl > $R/m1dev/dev252b-291.log 2>&1
waitload M1C-dev258
PY scripts/claude_corr252_run.py --agent $A252C --config $C252C --cases $D8 --work $W/dev258-252c --out $R/m1dev/dev258-252c.jsonl > $R/m1dev/dev258-252c.log 2>&1
PY scripts/claude_corr252_run.py --agent $A291 --config $C291 --cases $D8 --work $W/dev258-291 --out $R/m1dev/dev258-291.jsonl > $R/m1dev/dev258-291.log 2>&1
waitload M1C-dev259
PY scripts/claude_corr252_run.py --agent $A252C --config $C252C --cases $D9 --work $W/dev259-252c --out $R/m1dev/dev259-252c.jsonl > $R/m1dev/dev259-252c.log 2>&1
PY scripts/claude_corr252_run.py --agent $A291 --config $C291 --cases $D9 --work $W/dev259-291 --out $R/m1dev/dev259-291.jsonl > $R/m1dev/dev259-291.log 2>&1
SPY scripts/claude_291_score.py m1 $R/m1dev $PRED $R/m1-check.json > $R/m1-check.txt 2>&1
# M2 -- frozen suites vs 138nb's saved rows
waitload M2-suites
PY scripts/fable_suitediff218.py --agent $A291 --config $C291 --base-dir $NBRUN/sd \
  --out $R/sd --only sessions152,bench,marks123 > $R/sd.log 2>&1
# rt136 labels vs 138j's sealed rows (as 138n/138nb did); every 291 row is
# also compared directly with fresh 138nb rows from the same session.
waitload M2-rt136-291
PY scripts/fable_suitediff218.py --agent $A291 --config $C291 \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M2-rt136-nb
PY scripts/fable_suitediff218.py --agent $ANB --config $CNB \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136-nb --only rt136 > $R/sd136-nb.log 2>&1
waitload M2-rt143
PY scripts/claude_138l_rt143nogate.py $ANB $CNB $R/rt143nogate-nb.json > $R/rt143nogate-nb.log 2>&1
PY scripts/claude_138l_rt143nogate.py $A291 $C291 $R/rt143nogate-291.json > $R/rt143nogate-291.log 2>&1
# M3 -- sleep smoke on 291 (base: 138n's saved smoke-n.json, same as 138nb's)
waitload M3
PY scripts/fable_sleepsmoke206.py --agent $A291 --config $C291 --root $W/smoke-291 \
  --report $R/smoke-291.json --label 291 --idle-seconds 5.0 > $R/smoke-291.log 2>&1
# M4 -- 3 back-to-back bench reruns on 291
for i in 1 2 3; do
  waitload M4-$i
  PY scripts/fable_suitediff218.py --agent $A291 --config $C291 --base-dir $NBRUN/sd \
    --out $R/bench$i --only bench > $R/bench$i.log 2>&1
done
# M5 -- latency, alternating processes nb,291,nb,291,nb,291, 2 reps each
for i in 1 2 3; do for arm in nb 291; do
  waitload M5-$arm-$i
  if [ $arm = nb ]; then AG=$ANB; CF=$CNB; else AG=$A291; CF=$C291; fi
  PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$arm-$i 2 $R/lat-$arm-$i.json \
    $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json > $R/lat-$arm-$i.log 2>&1
done; done
# M6 -- restart dialogs (138j p3 set + 138k v set) on 138nb and 291
for arm in nb 291; do
  waitload M6-restart-$arm
  if [ $arm = nb ]; then AG=$ANB; CF=$CNB; else AG=$A291; CF=$C291; fi
  for probe in $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json \
           $VK/v-dialogs.json $VK/v-supp.json; do
    b=$(basename $probe .json)
    PY scripts/claude_merge138k_probe.py $AG $CF $W/probe-$arm-$b $probe \
      $R/probe/$arm-$b.json > $R/probe/$arm-$b.txt 2>&1
  done
done
# M6 -- verifier dialogs (138m's M6 files) on 138nb and 291
for arm in nb 291; do
  waitload M6-verifier-$arm
  if [ $arm = nb ]; then AG=$ANB; CF=$CNB; else AG=$A291; CF=$C291; fi
  PY $VM/run_probes.py $AG $CF $W/vp-$arm $VM/probes.json $R/vp-nb-291-tmp-$arm.json > $R/vp-$arm.log 2>&1
  PY $VM/run_probes.py $AG $CF $W/vs-$arm $VM/probes-supp.json $R/vs-nb-291-tmp-$arm.json > $R/vs-$arm.log 2>&1
done
mv $R/vp-nb-291-tmp-nb.json $R/vp-nb-probes.json
mv $R/vp-nb-291-tmp-291.json $R/vp-291-probes.json
mv $R/vs-nb-291-tmp-nb.json $R/vp-nb-supp.json
mv $R/vs-nb-291-tmp-291.json $R/vp-291-supp.json
PY scripts/claude_291_score.py m2m6 $R $PRED $R/score291.json > $R/score.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a "$R/uptime.log"
cat $R/m1720-judge.txt $R/m1-check.txt $R/score.txt
