#!/bin/bash
# Exp 268b registered runs: DEV record + M2 invpanel + M3 frozen suites +
# M4 latency, one heavy suite at a time, `uptime` + `df` checked before
# each step (waits while 1-min load > 60). M1 (nhoppanel268b) runs
# separately after the panel SEAL appears, once per arm.
# usage: scripts/claude_268b_runall.sh <run_dir>
# New file only. CPU only.
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
AB=scripts/claude_loop138nb_agent.py
CB=artifacts/claude-merge138nb-20260923/loop138nb-config.json
AN=scripts/claude_loop268b_agent.py
CN=artifacts/claude-nhop268b-20260923/loop268b-config.json
PRED=artifacts/claude-nhop268b-20260923/predicted_moves268b.json
INVP=artifacts/claude-invpanel138nb-20260923
NB=artifacts/claude-merge138nb-20260923/run
A138N=artifacts/claude-merge138n-20260922
V=artifacts/claude-verify-20260922/138j
VK=artifacts/claude-verify-20260922/138k
W=$R/work
mkdir -p "$R" "$W" "$R/dev" "$R/probe" "$R/inv" "$R/m1"
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
# DEV -- registered dev record on both arms (70 rerun + 7 supp + 46 new)
waitload DEV-b
PY scripts/claude_268b_devrepro.py $AB $CB $R/dev/dev-138nb.json dev-138nb \
  > $R/dev/dev-138nb.log 2>&1 || echo "ERR DEV b" | tee -a $R/errors.txt
waitload DEV-n
PY scripts/claude_268b_devrepro.py $AN $CN $R/dev/dev-268b.json dev-268b \
  > $R/dev/dev-268b.log 2>&1 || echo "ERR DEV n" | tee -a $R/errors.txt
# M2 -- invpanel138nb regression, once per arm, sealed score_panel.py
waitload M2-b
PY scripts/claude_268b_panelrun.py $INVP/panel.jsonl $AB $CB $W/inv-138nb.jsonl inv-138nb \
  > $R/inv/inv-138nb.log 2>&1 || echo "ERR M2 b" | tee -a $R/errors.txt
waitload M2-n
PY scripts/claude_268b_panelrun.py $INVP/panel.jsonl $AN $CN $W/inv-268b.jsonl inv-268b \
  > $R/inv/inv-268b.log 2>&1 || echo "ERR M2 n" | tee -a $R/errors.txt
PY $INVP/score_panel.py $INVP/panel.jsonl $W/inv-138nb.jsonl $W/inv-138nb-score.json \
  > $R/inv/inv-138nb-score.log 2>&1 || echo "ERR M2 score b" | tee -a $R/errors.txt
PY $INVP/score_panel.py $INVP/panel.jsonl $W/inv-268b.jsonl $W/inv-268b-score.json \
  > $R/inv/inv-268b-score.log 2>&1 || echo "ERR M2 score n" | tee -a $R/errors.txt
# M3 -- frozen suites vs 138nb's saved rows
waitload M3-suites
PY scripts/fable_suitediff218.py --agent $AN --config $CN --base-dir $NB/sd \
  --out $R/sd --only sessions152,bench,marks123 > $R/sd.log 2>&1
waitload M3-rt136
PY scripts/fable_suitediff218.py --agent $AN --config $CN \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M3-rt143
PY scripts/claude_138l_rt143nogate.py $AN $CN $R/rt143nogate-268b.json > $R/rt143nogate.log 2>&1
# M3 -- restart + verifier probes on 268b (diffed vs 138nb's saved nb rows)
i=0
for p in $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json \
         $VK/v-dialogs.json $VK/v-supp.json \
         $A138N/v138m-probes-dialogs.json $A138N/v138m-probes-supp-dialogs.json; do
  b=$(basename $p .json)
  i=$((i+1))
  waitload M3probe-$b
  PY scripts/claude_merge138k_probe.py $AN $CN $W/probe-268b-$b $p \
    $R/probe/268b-$b.json > $R/probe/268b-$b.txt 2>&1 || echo "ERR M3 $b" | tee -a $R/errors.txt
done
# M4 -- latency, alternating processes b,n,b,n,b,n, 2 reps each
i=0
for a in b n b n b n; do
  i=$((i+1))
  waitload M4-$a-$i
  if [ $a = b ]; then AG=$AB; CF=$CB; else AG=$AN; CF=$CN; fi
  PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$a-$i 2 $R/lat-$a-$i.json \
    $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json > $R/lat-$a-$i.log 2>&1
done
PY scripts/claude_268b_score.py $R $PRED $R/score268b.json > $R/score.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
cat $R/score.txt
