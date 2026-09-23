#!/bin/bash
# Merge 138nb -- registered commands for M2-M5 (M1 invpanel and M6
# tablepanel221 run separately, TEST-ONLY, once each, after the seal).
# Base for M2/M3 = 138n's SAVED rows (artifacts/claude-merge138n-20260922/run).
# usage: scripts/claude_138nb_runall.sh <run_dir>
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
AN=scripts/claude_loop138n_agent.py
CN=artifacts/claude-merge138n-20260922/loop138n-config.json
AB=scripts/claude_loop138nb_agent.py
CB=artifacts/claude-merge138nb-20260923/loop138nb-config.json
PRED=${PRED:-artifacts/claude-merge138nb-20260923/predicted_moves138nb.json}
A=artifacts/claude-merge138n-20260922
V=artifacts/claude-verify-20260922/138j
VK=artifacts/claude-verify-20260922/138k
NB=$A/run
W=$R/work
mkdir -p "$R" "$W" "$R/m2" "$R/probe"
waitload() {
  while :; do
    L=$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
    echo "$(date +%T) uptime load1=$L before: $1" | tee -a "$R/uptime.log"
    df -g / | tail -1 | tee -a "$R/uptime.log"
    awk -v l="$L" 'BEGIN{exit !(l<=60)}' && break
    sleep 30
  done
}
T0=$(date +%s)
# M2 -- 138n's M1 dev/case files (720) on 138n and 138nb
for a in n nb; do
  waitload M2-$a
  PY scripts/claude_138nb_m2.py run --arm $a --out-dir $R/m2 --work $W/m2-$a \
    > $R/m2-log-$a.txt 2>&1 || echo "ERR M2 $a" | tee -a $R/errors.txt
done
PY scripts/claude_138nb_m2.py judge --dir $R/m2 --pred $PRED --out $R/m2-judge.json > $R/m2-judge.txt 2>&1
# M3 -- frozen suites vs 138n's saved rows
waitload M3-suites
PY scripts/fable_suitediff218.py --agent $AB --config $CB --base-dir $NB/sd \
  --out $R/sd --only sessions152,bench,marks123 > $R/sd.log 2>&1
# rt136 labels vs 138j's sealed rows (as 138n did); the scorer also compares
# every row directly with 138n's saved run/sd136/rt136-rows.json.
waitload M3-rt136
PY scripts/fable_suitediff218.py --agent $AB --config $CB \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M3-rt143
PY scripts/claude_138l_rt143nogate.py $AB $CB $R/rt143nogate-nb.json > $R/rt143nogate.log 2>&1
# M3 probes -- 138n's restart/verifier M6 dialogs, 138n fresh and 138nb
for a in n nb; do
  waitload M3probe-$a
  if [ $a = n ]; then AG=$AN; CF=$CN; else AG=$AB; CF=$CB; fi
  for p in $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json \
           $VK/v-dialogs.json $VK/v-supp.json \
           $A/v138m-probes-dialogs.json $A/v138m-probes-supp-dialogs.json; do
    b=$(basename $p .json)
    PY scripts/claude_merge138k_probe.py $AG $CF $W/probe-$a-$b $p \
      $R/probe/$a-$b.json > $R/probe/$a-$b.txt 2>&1
  done
done
# M4 -- sleep smoke on 138nb (base: 138n's saved smoke-n.json)
waitload M4-smoke
PY scripts/fable_sleepsmoke206.py --agent $AB --config $CB --root $W/smoke-nb \
  --report $R/smoke-nb.json --label nb --idle-seconds 5.0 > $R/smoke-nb.log 2>&1
# M4 -- 3 back-to-back bench reruns on 138nb
for i in 1 2 3; do
  waitload M4-bench-$i
  PY scripts/fable_suitediff218.py --agent $AB --config $CB --base-dir $NB/sd \
    --out $R/bench$i --only bench > $R/bench$i.log 2>&1
done
# M5 -- latency, alternating processes n,nb,n,nb,n,nb, 2 reps each
for i in 1 2 3; do for a in n nb; do
  waitload M5-$a-$i
  if [ $a = n ]; then AG=$AN; CF=$CN; else AG=$AB; CF=$CB; fi
  PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$a-$i 2 $R/lat-$a-$i.json \
    $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json > $R/lat-$a-$i.log 2>&1
done; done
PY scripts/claude_138nb_score.py $R $PRED $R/score138nb.json > $R/score.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a "$R/uptime.log"
cat $R/m2-judge.txt $R/score.txt
