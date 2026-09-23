#!/bin/bash
# Exp 268 registered runs M2-M4 (+ registered dev record), one heavy suite
# at a time, `uptime` checked before each step (waits while 1-min load > 60).
# usage: scripts/claude_268_runall.sh <run_dir>
# New file only. CPU only.
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
AM=scripts/claude_loop138m_agent.py
CM=artifacts/claude-merge138m-20260922/loop138m-config.json
AN=scripts/claude_loop268_agent.py
CN=artifacts/claude-nhop268-20260923/loop268-config.json
PRED=artifacts/claude-nhop268-20260923/predicted_moves268.json
V=artifacts/claude-verify-20260922/138j
VK=artifacts/claude-verify-20260922/138k
VM=artifacts/claude-verify-20260922/138m
LB=artifacts/claude-merge138m-20260922/run/sd
W=$R/work
mkdir -p "$R" "$W" "$R/dev" "$R/probe"
waitload() {
  while :; do
    L=$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
    echo "$(date +%T) uptime load1=$L before: $1" | tee -a "$R/uptime.log"
    awk -v l="$L" 'BEGIN{exit !(l<=60)}' && break
    sleep 30
  done
}
T0=$(date +%s)
# DEV -- registered dev record on both arms (36 dev + 34 own + 7 supp)
waitload DEV-m
PY scripts/claude_268_devrepro.py $AM $CM $R/dev/dev-138m.json dev-138m \
  > $R/dev/dev-138m.log 2>&1 || echo "ERR DEV m" | tee -a $R/errors.txt
waitload DEV-n
PY scripts/claude_268_devrepro.py $AN $CN $R/dev/dev-268.json dev-268 \
  > $R/dev/dev-268.log 2>&1 || echo "ERR DEV n" | tee -a $R/errors.txt
waitload SUPP-m
PY scripts/claude_268_supp.py $AM $CM $R/dev/supp-138m.json supp-138m \
  > $R/dev/supp-138m.log 2>&1 || echo "ERR SUPP m" | tee -a $R/errors.txt
waitload SUPP-n
PY scripts/claude_268_supp.py $AN $CN $R/dev/supp-268.json supp-268 \
  > $R/dev/supp-268.log 2>&1 || echo "ERR SUPP n" | tee -a $R/errors.txt
# M2 -- frozen suites vs 138m's saved rows
waitload M2-suites
PY scripts/fable_suitediff218.py --agent $AN --config $CN --base-dir $LB \
  --out $R/sd --only sessions152,bench,marks123 > $R/sd.log 2>&1
waitload M2-rt136
PY scripts/fable_suitediff218.py --agent $AN --config $CN \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M2-rt143
PY scripts/claude_138l_rt143nogate.py $AN $CN $R/rt143nogate-268.json > $R/rt143nogate.log 2>&1
# M3 -- restart + verifier probes on 268 (diffed vs 138m's saved rows)
for p in p3-dialogs p3c-restart2 p3d-ghost; do
  waitload M3-$p
  PY scripts/claude_merge138k_probe.py $AN $CN $W/probe-268-$p $V/$p.json \
    $R/probe/268-$p.json > $R/probe/268-$p.txt 2>&1
done
for p in v-dialogs v-supp; do
  waitload M3-$p
  PY scripts/claude_merge138k_probe.py $AN $CN $W/probe-268-$p $VK/$p.json \
    $R/probe/268-$p.json > $R/probe/268-$p.txt 2>&1
done
waitload M3-probes
PY artifacts/claude-verify-20260922/138m/run_probes.py $AN $CN $W/vp268 \
  $VM/probes.json $R/probe/268-probes.json > $R/probe/268-probes.txt 2>&1
waitload M3-supp
PY artifacts/claude-verify-20260922/138m/run_probes.py $AN $CN $W/vs268 \
  $VM/probes-supp.json $R/probe/268-supp.json > $R/probe/268-supp.txt 2>&1
# M4 -- latency, alternating processes m,n,m,n,m,n, 2 reps each
i=0
for a in m n m n m n; do
  i=$((i+1))
  waitload M4-$a-$i
  if [ $a = m ]; then AG=$AM; CF=$CM; else AG=$AN; CF=$CN; fi
  PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$a-$i 2 $R/lat-$a-$i.json \
    $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json > $R/lat-$a-$i.log 2>&1
done
PY scripts/claude_268_score.py $R $PRED $R/score268.json > $R/score.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/score.txt
