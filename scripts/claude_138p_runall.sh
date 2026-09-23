#!/bin/bash
# Merge 138p -- registered marks M1-M6, in order, one heavy step at a time,
# `uptime` checked before each step (waits while 1-min load > 60).
# usage: scripts/claude_138p_runall.sh <run_dir>
# M7 (blind panels) runs separately: scripts/claude_138p_panel.sh <run_dir>
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
SPY() { uv run --offline --no-project --python 3.12 python -B "$@"; }
AM=scripts/claude_loop138m_agent.py
CM=artifacts/claude-merge138m-20260922/loop138m-config.json
AP=scripts/claude_loop138p_agent.py
CP=artifacts/claude-merge138p-20260923/loop138p-config.json
PRED=artifacts/claude-merge138p-20260923/predicted_moves138p.json
D2=artifacts/claude-correct252b-20260922/dev252b.jsonl
D8=artifacts/claude-comment258-20260922/dev258.jsonl
D9=artifacts/claude-boundary259-20260922/dev259.jsonl
DEV260=artifacts/claude-openers260-20260922/devcases260.json
A260=scripts/claude_loop260_agent.py
C260=artifacts/claude-openers260-20260922/loop260-config.json
A252C=scripts/claude_loop252c_agent.py
C252C=artifacts/claude-merge252c-20260922/loop252c-config.json
A252B=scripts/claude_loop252b_agent.py
C252B=artifacts/claude-correct252b-20260922/loop252b-config.json
A258=scripts/claude_loop258_agent.py
C258=artifacts/claude-comment258-20260922/loop258-config.json
A259=scripts/claude_loop259_agent.py
C259=artifacts/claude-boundary259-20260922/loop259-config.json
V=artifacts/claude-verify-20260922/138j
VK=artifacts/claude-verify-20260922/138k
VM=artifacts/claude-verify-20260922/138m
MB=artifacts/claude-merge138m-20260922/run/sd
W=$R/work
mkdir -p "$R" "$W" "$R/l1" "$R/probe" "$R/m1dev"
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
# M1A -- 138m's nine piece case sets on own / head / 138m / 138p
for a in own head m; do
  waitload M1A-$a
  PY scripts/claude_138m_l1.py run --arm $a --out-dir $R/l1 --work $W/l1-$a \
    > $R/l1-log-$a.txt 2>&1 || echo "ERR M1A $a" | tee -a $R/errors.txt
done
waitload M1A-p
PY scripts/claude_138p_l1.py run --out-dir $R/l1 --work $W/l1-p \
  > $R/l1-log-p.txt 2>&1 || echo "ERR M1A p" | tee -a $R/errors.txt
PY scripts/claude_138m_l1.py sealed --dir $R/l1 --out $R/l1-sealed.json > $R/l1-sealed.txt 2>&1
PY scripts/claude_138p_l1.py judge --dir $R/l1 --pred $PRED --out $R/l1-judge.json > $R/l1-judge.txt 2>&1
# M1B -- 260 devcases on 260 (own), 138m, 138p
waitload M1B-260dev
PY scripts/claude_openers260_run.py dev $A260 $C260 $W/dev260-own $DEV260 $R/m1dev/dev260-own.json > $R/m1dev/dev260-own.log 2>&1
PY scripts/claude_openers260_run.py dev $AM $CM $W/dev260-m $DEV260 $R/m1dev/dev260-m.json > $R/m1dev/dev260-m.log 2>&1
PY scripts/claude_openers260_run.py dev $AP $CP $W/dev260-p $DEV260 $R/m1dev/dev260-p.json > $R/m1dev/dev260-p.log 2>&1
# M1C -- 252c devs on 252c (own), 138m, 138p (+ same-session other arms)
waitload M1C-dev252b
PY scripts/claude_corr252_run.py --agent $A252C --config $C252C --cases $D2 --work $W/dev252b-252c --out $R/m1dev/dev252b-252c.jsonl > $R/m1dev/dev252b-252c.log 2>&1
PY scripts/claude_corr252_run.py --agent $AM --config $CM --cases $D2 --work $W/dev252b-m --out $R/m1dev/dev252b-m.jsonl > $R/m1dev/dev252b-m.log 2>&1
PY scripts/claude_corr252_run.py --agent $AP --config $CP --cases $D2 --work $W/dev252b-p --out $R/m1dev/dev252b-p.jsonl > $R/m1dev/dev252b-p.log 2>&1
waitload M1C-dev258
PY scripts/claude_corr252_run.py --agent $A252C --config $C252C --cases $D8 --work $W/dev258-252c --out $R/m1dev/dev258-252c.jsonl > $R/m1dev/dev258-252c.log 2>&1
PY scripts/claude_corr252_run.py --agent $AM --config $CM --cases $D8 --work $W/dev258-m --out $R/m1dev/dev258-m.jsonl > $R/m1dev/dev258-m.log 2>&1
PY scripts/claude_corr252_run.py --agent $AP --config $CP --cases $D8 --work $W/dev258-p --out $R/m1dev/dev258-p.jsonl > $R/m1dev/dev258-p.log 2>&1
PY scripts/claude_corr252_run.py --agent $A258 --config $C258 --cases $D8 --work $W/dev258-258 --out $R/m1dev/dev258-258.jsonl > $R/m1dev/dev258-258.log 2>&1
waitload M1C-dev259
PY scripts/claude_corr252_run.py --agent $A252C --config $C252C --cases $D9 --work $W/dev259-252c --out $R/m1dev/dev259-252c.jsonl > $R/m1dev/dev259-252c.log 2>&1
PY scripts/claude_corr252_run.py --agent $AM --config $CM --cases $D9 --work $W/dev259-m --out $R/m1dev/dev259-m.jsonl > $R/m1dev/dev259-m.log 2>&1
PY scripts/claude_corr252_run.py --agent $AP --config $CP --cases $D9 --work $W/dev259-p --out $R/m1dev/dev259-p.jsonl > $R/m1dev/dev259-p.log 2>&1
PY scripts/claude_corr252_run.py --agent $A259 --config $C259 --cases $D9 --work $W/dev259-259 --out $R/m1dev/dev259-259.jsonl > $R/m1dev/dev259-259.log 2>&1
SPY scripts/claude_138p_score.py m1 $R/m1dev $PRED $R/m1-check.json > $R/m1-check.txt 2>&1
# M2 -- frozen suites vs 138m's saved rows
waitload M2-suites
PY scripts/fable_suitediff218.py --agent $AP --config $CP --base-dir $MB \
  --out $R/sd --only sessions152,bench,marks123 > $R/sd.log 2>&1
waitload M2-rt136
PY scripts/fable_suitediff218.py --agent $AP --config $CP \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M2-rt143
PY scripts/claude_138l_rt143nogate.py $AP $CP $R/rt143nogate-p.json > $R/rt143nogate.log 2>&1
# M3 -- sleep smoke on 138p (vs 138m's saved smoke-m.json)
waitload M3
PY scripts/fable_sleepsmoke206.py --agent $AP --config $CP --root $W/smoke-p \
  --report $R/smoke-p.json --label p --idle-seconds 5.0 > $R/smoke-p.log 2>&1
# M4 -- 3 back-to-back bench reruns on 138p
for i in 1 2 3; do
  waitload M4-$i
  PY scripts/fable_suitediff218.py --agent $AP --config $CP --base-dir $MB \
    --out $R/bench$i --only bench > $R/bench$i.log 2>&1
done
# M5 -- latency, alternating processes m,p,m,p,m,p, 2 reps each
for i in 1 2 3; do for a in m p; do
  waitload M5-$a-$i
  if [ $a = m ]; then AG=$AM; CF=$CM; else AG=$AP; CF=$CP; fi
  PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$a-$i 2 $R/lat-$a-$i.json \
    $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json > $R/lat-$a-$i.log 2>&1
done; done
# M6 -- restart and verifier dialogs (138j p3 set + 138k v set + 138m probes)
for a in m p; do
  waitload M6-$a
  if [ $a = m ]; then AG=$AM; CF=$CM; else AG=$AP; CF=$CP; fi
  for p in $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json \
           $VK/v-dialogs.json $VK/v-supp.json; do
    b=$(basename $p .json)
    PY scripts/claude_merge138k_probe.py $AG $CF $W/probe-$a-$b $p \
      $R/probe/$a-$b.json > $R/probe/$a-$b.txt 2>&1
  done
  PY $VM/run_probes.py $AG $CF $W/vp-$a $VM/probes.json $R/vp-$a.json > $R/vp-$a.log 2>&1
  PY $VM/run_probes.py $AG $CF $W/vs-$a $VM/probes-supp.json $R/vs-$a.json > $R/vs-$a.log 2>&1
done
PY scripts/claude_138p_score.py m2m6 $R $PRED $R/score138p.json > $R/score.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/l1-sealed.txt $R/l1-judge.txt $R/m1-check.txt $R/score.txt
