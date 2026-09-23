#!/bin/bash
# Merge 292 -- registered marks M1-M4, in order, one heavy step at a time,
# `uptime` checked before each step (waits while 1-min load > 60, stops
# under 3 GB free). usage: scripts/claude_292_runall.sh <run_dir>
# M5 (fresh blind mixpanel) runs separately: scripts/claude_292_m5.sh <tmpdir>
# corrpanel291 runs with scripts/claude_corr252_run.py unchanged (it takes
# --agent, so the same runner serves the 291 fidelity arm and 292).
set -u
R=$1
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B "$@"; }
SPY() { uv run --offline --no-project --python 3.12 python -B "$@"; }
A291=scripts/claude_loop291_agent.py
C291=artifacts/claude-join291-20260923/loop291-config.json
A292=scripts/claude_loop292_agent.py
C292=artifacts/claude-merge292-20260923/loop292-config.json
A266B=scripts/claude_loop266b_agent.py
C266B=artifacts/claude-chain266b-20260923/loop266b-config.json
A268B=scripts/claude_loop268b_agent.py
C268B=artifacts/claude-nhop268b-20260923/loop268b-config.json
A293=scripts/claude_loop293_agent.py
C293=artifacts/claude-yesno293-20260923/loop293-config.json
PRED=artifacts/claude-merge292-20260923/predicted_moves292.json
NBRUN=artifacts/claude-join291-20260923/run
P266B=artifacts/claude-chainpanel266b-20260923
P268B=artifacts/claude-nhoppanel268b-20260923
P293=artifacts/claude-yesnopanel293-20260923
P291=artifacts/claude-corrpanel291-20260923
V=artifacts/claude-verify-20260922/138j
VK=artifacts/claude-verify-20260922/138k
VM=artifacts/claude-verify-20260922/138m
W=$R/work
mkdir -p "$R" "$W" "$R/m1" "$R/probe"
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
# ---- M1 fidelity re-run first, then the same runner and scorer on 292 ----
# chainpanel266b: fidelity arm 266b, then 292 (same runner + sealed scorer)
waitload M1-chain-fidelity
PY scripts/claude_292_panelrun.py --panel chain266b --arm 266b --out $R/m1/chain266b-266b.jsonl > $R/m1/chain266b-266b.log 2>&1
SPY $P266B/score_panel.py $P266B/panel.jsonl $R/m1/chain266b-266b.jsonl > $R/m1/score-chain266b-266b.txt 2>&1
echo "score chain fidelity exit $?" | tee -a $R/uptime.log
waitload M1-chain-292
PY scripts/claude_292_panelrun.py --panel chain266b --arm 292 --out $R/m1/chain266b-292.jsonl > $R/m1/chain266b-292.log 2>&1
SPY $P266B/score_panel.py $P266B/panel.jsonl $R/m1/chain266b-292.jsonl > $R/m1/score-chain266b-292.txt 2>&1
SPY scripts/claude_292_score.py m1 --panel chain266b --piece-score $R/m1/score-chain266b-266b.txt --new-score $R/m1/score-chain266b-292.txt --out $R/m1/check-chain266b.json > $R/m1/check-chain266b.txt 2>&1
# nhoppanel268b: fidelity arm 268b, then 292
waitload M1-nhop-fidelity
PY scripts/claude_292_panelrun.py --panel nhop268b --arm 268b --out $R/m1/nhop268b-268b.jsonl > $R/m1/nhop268b-268b.log 2>&1
SPY $P268B/score_panel.py $P268B/panel.jsonl $R/m1/nhop268b-268b.jsonl $R/m1/score-nhop268b-268b.json > $R/m1/score-nhop268b-268b.log 2>&1
echo "score nhop fidelity exit $?" | tee -a $R/uptime.log
waitload M1-nhop-292
PY scripts/claude_292_panelrun.py --panel nhop268b --arm 292 --out $R/m1/nhop268b-292.jsonl > $R/m1/nhop268b-292.log 2>&1
SPY $P268B/score_panel.py $P268B/panel.jsonl $R/m1/nhop268b-292.jsonl $R/m1/score-nhop268b-292.json > $R/m1/score-nhop268b-292.log 2>&1
SPY scripts/claude_292_score.py m1 --panel nhop268b --piece-score $R/m1/score-nhop268b-268b.json --new-score $R/m1/score-nhop268b-292.json --out $R/m1/check-nhop268b.json > $R/m1/check-nhop268b.txt 2>&1
# yesnopanel293: fidelity arm 293, then 292
waitload M1-yesno-fidelity
PY scripts/claude_292_panelrun.py --panel yesno293 --arm 293 --out $R/m1/yesno293-293.jsonl > $R/m1/yesno293-293.log 2>&1
SPY $P293/score_panel.py $P293/panel.jsonl $R/m1/yesno293-293.jsonl $R/m1/score-yesno293-293.json > $R/m1/score-yesno293-293.log 2>&1
echo "score yesno fidelity exit $?" | tee -a $R/uptime.log
waitload M1-yesno-292
PY scripts/claude_292_panelrun.py --panel yesno293 --arm 292 --out $R/m1/yesno293-292.jsonl > $R/m1/yesno293-292.log 2>&1
SPY $P293/score_panel.py $P293/panel.jsonl $R/m1/yesno293-292.jsonl $R/m1/score-yesno293-292.json > $R/m1/score-yesno293-292.log 2>&1
SPY scripts/claude_292_score.py m1 --panel yesno293 --piece-score $R/m1/score-yesno293-293.json --new-score $R/m1/score-yesno293-292.json --out $R/m1/check-yesno293.json > $R/m1/check-yesno293.txt 2>&1
# corrpanel291: same runner (claude_corr252_run.py) on 291 then 292, sealed scorer
waitload M1-corr-fidelity
PY scripts/claude_corr252_run.py --agent $A291 --config $C291 --cases $P291/panel.jsonl --work $W/m1-corr-291 --out $R/m1/corr291-291.jsonl > $R/m1/corr291-291.log 2>&1
SPY $P291/score_panel.py $P291/panel.jsonl $R/m1/corr291-291.jsonl > $R/m1/score-corr291-291.txt 2>&1
echo "score corr fidelity exit $?" | tee -a $R/uptime.log
waitload M1-corr-292
PY scripts/claude_corr252_run.py --agent $A292 --config $C292 --cases $P291/panel.jsonl --work $W/m1-corr-292 --out $R/m1/corr291-292.jsonl > $R/m1/corr291-292.log 2>&1
SPY $P291/score_panel.py $P291/panel.jsonl $R/m1/corr291-292.jsonl > $R/m1/score-corr291-292.txt 2>&1
SPY scripts/claude_292_score.py m1 --panel corr291 --piece-score $R/m1/score-corr291-291.txt --new-score $R/m1/score-corr291-292.txt --piece-rows $R/m1/corr291-291.jsonl --new-rows $R/m1/corr291-292.jsonl --out $R/m1/check-corr291.json > $R/m1/check-corr291.txt 2>&1
cat $R/m1/check-*.txt
# ---- M2 frozen suites vs 291's saved rows ----
waitload M2-suites
PY scripts/fable_suitediff218.py --agent $A292 --config $C292 --base-dir $NBRUN/sd \
  --out $R/sd --only sessions152,bench,marks123 > $R/sd.log 2>&1
waitload M2-rt136-292
PY scripts/fable_suitediff218.py --agent $A292 --config $C292 \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136 --only rt136 > $R/sd136.log 2>&1
waitload M2-rt136-291
PY scripts/fable_suitediff218.py --agent $A291 --config $C291 \
  --base-dir artifacts/fable-agent138j-20260922 --out $R/sd136-291 --only rt136 > $R/sd136-291.log 2>&1
waitload M2-rt143
PY scripts/claude_138l_rt143nogate.py $A291 $C291 $R/rt143nogate-291.json > $R/rt143nogate-291.log 2>&1
PY scripts/claude_138l_rt143nogate.py $A292 $C292 $R/rt143nogate-292.json > $R/rt143nogate-292.log 2>&1
# ---- M3 restart + verifier dialogs (291's M6 files) on 291 and 292 ----
for arm in 291 292; do
  waitload M3-restart-$arm
  if [ $arm = 291 ]; then AG=$A291; CF=$C291; else AG=$A292; CF=$C292; fi
  for probe in $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json \
           $VK/v-dialogs.json $VK/v-supp.json; do
    b=$(basename $probe .json)
    PY scripts/claude_merge138k_probe.py $AG $CF $W/probe-$arm-$b $probe \
      $R/probe/$arm-$b.json > $R/probe/$arm-$b.txt 2>&1
  done
done
for arm in 291 292; do
  waitload M3-verifier-$arm
  if [ $arm = 291 ]; then AG=$A291; CF=$C291; else AG=$A292; CF=$C292; fi
  PY $VM/run_probes.py $AG $CF $W/vp-$arm $VM/probes.json $R/vp-291-292-tmp-$arm.json > $R/vp-$arm.log 2>&1
  PY $VM/run_probes.py $AG $CF $W/vs-$arm $VM/probes-supp.json $R/vs-291-292-tmp-$arm.json > $R/vs-$arm.log 2>&1
done
mv $R/vp-291-292-tmp-291.json $R/vp-291-probes.json
mv $R/vp-291-292-tmp-292.json $R/vp-292-probes.json
mv $R/vs-291-292-tmp-291.json $R/vp-291-supp.json
mv $R/vs-291-292-tmp-292.json $R/vp-292-supp.json
# ---- M4 latency, alternating processes 291,292,291,292,291,292 ----
for i in 1 2 3; do for arm in 291 292; do
  waitload M4-$arm-$i
  if [ $arm = 291 ]; then AG=$A291; CF=$C291; else AG=$A292; CF=$C292; fi
  PY scripts/claude_merge138k_latency.py $AG $CF $W/lat-$arm-$i 2 $R/lat-$arm-$i.json \
    $V/p3-dialogs.json $V/p3c-restart2.json $V/p3d-ghost.json > $R/lat-$arm-$i.log 2>&1
done; done
SPY scripts/claude_292_score.py m2m6 --dir $R --pred $PRED $R/score292.json > $R/score.txt 2>&1
echo "TOTAL $(( $(date +%s) - T0 )) s" | tee -a "$R/uptime.log"
cat $R/score.txt
