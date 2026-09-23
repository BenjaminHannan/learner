#!/bin/bash
# Exp 293 registered runs: DEV record (both arms) + M2 inv/chain panels +
# M3 frozen suites + M4 restart/verifier probes + M5 latency, one heavy
# suite at a time, `uptime` + `df -g` checked before each step (waits
# while the 1-min load is above 60). M1 (yesnopanel293) runs separately
# after the panel SEAL appears, once per arm.
# usage: scripts/claude_293_runall2.sh <run_dir> (fix1: W used before set under set -u; use $R/work directly)
# New file only. CPU only.
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
AB=scripts/claude_loop138nb_agent.py
CB=artifacts/claude-merge138nb-20260923/loop138nb-config.json
AN=scripts/claude_loop293_agent.py
CN=artifacts/claude-yesno293-20260923/loop293-config.json
INVP=$R/work/invpanel.jsonl
CHNPP=$R/work/chainpanel.jsonl
NBSD=artifacts/claude-merge138nb-20260923/run/sd
J138=artifacts/fable-agent138j-20260922
V=artifacts/claude-verify-20260922/138j
VK=artifacts/claude-verify-20260922/138k
A138N=artifacts/claude-merge138n-20260922
W=$R/work
mkdir -p "$R" "$W" "$R/dev" "$R/probe" "$R/inv" "$R/chain"
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
# M2 panels, extracted unchanged from origin/builder-outbox at run time
git show origin/builder-outbox:artifacts/claude-invpanel138nb-20260923/panel.jsonl > $INVP
git show origin/builder-outbox:artifacts/claude-chainpanel266b-20260923/panel.jsonl > $CHNPP
wc -l $INVP $CHNPP | tee -a "$R/uptime.log"
# DEV -- registered dev record on both arms (111 dialogs)
waitload DEV-b
PY scripts/claude_293_repro.py $AB $CB $R/dev/dev-138nb.jsonl dev-138nb \
  > $R/dev/dev-138nb.log 2>&1 || echo "ERR DEV b" | tee -a $R/errors.txt
waitload DEV-n
PY scripts/claude_293_repro.py $AN $CN $R/dev/dev-293.jsonl dev-293 \
  > $R/dev/dev-293.log 2>&1 || echo "ERR DEV n" | tee -a $R/errors.txt
# M2 -- invpanel + chainpanel regression, once per arm
waitload M2-inv-b
PY scripts/claude_293_reg.py $INVP $AB $CB $W/inv-138nb.jsonl inv-138nb \
  > $R/inv/inv-138nb.log 2>&1 || echo "ERR M2 inv b" | tee -a $R/errors.txt
waitload M2-inv-n
PY scripts/claude_293_reg.py $INVP $AN $CN $W/inv-293.jsonl inv-293 \
  > $R/inv/inv-293.log 2>&1 || echo "ERR M2 inv n" | tee -a $R/errors.txt
waitload M2-chain-b
PY scripts/claude_293_reg.py $CHNPP $AB $CB $W/chain-138nb.jsonl chain-138nb \
  > $R/chain/chain-138nb.log 2>&1 || echo "ERR M2 chain b" | tee -a $R/errors.txt
waitload M2-chain-n
PY scripts/claude_293_reg.py $CHNPP $AN $CN $W/chain-293.jsonl chain-293 \
  > $R/chain/chain-293.log 2>&1 || echo "ERR M2 chain n" | tee -a $R/errors.txt
# M3 -- frozen suites vs 138nb's saved rows
waitload M3-suites
PY scripts/fable_suitediff218.py --agent $AN --config $CN --base-dir $NBSD \
  --out $R/sd --only sessions152,bench,marks123 > $R/sd.log 2>&1
waitload M3-rt136
PY scripts/fable_suitediff218.py --agent $AN --config $CN \
  --base-dir $J138 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M3-rt143
PY scripts/claude_138l_rt143nogate.py $AN $CN $R/rt143nogate-293.json > $R/rt143nogate.log 2>&1
# M4 -- restart + verifier probes on 293 (diffed vs 138nb runs)
i=0
for p in $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json \
         $VK/v-dialogs.json $VK/v-supp.json \
         $A138N/v138m-probes-dialogs.json $A138N/v138m-probes-supp-dialogs.json; do
  b=$(basename $p .json)
  i=$((i+1))
  waitload M4-$b
  PY scripts/claude_merge138k_probe.py $AN $CN $W/probe-293-$b $p \
    $R/probe/293-$b.json > $R/probe/293-$b.txt 2>&1 || echo "ERR M4 $b" | tee -a $R/errors.txt
done
# M5 -- latency, alternating processes b,n,b,n, 2 reps each
i=0
for a in b n b n; do
  i=$((i+1))
  waitload M5-$a-$i
  if [ $a = b ]; then AG=$AB; CF=$CB; else AG=$AN; CF=$CN; fi
  PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$a-$i 2 $R/lat-$a-$i.json \
    $V/p3-dialogs.json > $R/lat-$a-$i.log 2>&1 || echo "ERR M5 $a $i" | tee -a $R/errors.txt
done
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a $R/uptime.log
