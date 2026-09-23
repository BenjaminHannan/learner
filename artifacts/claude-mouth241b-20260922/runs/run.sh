#!/bin/bash
# exp 241b registered suite runs (post-seal). D6 wall protocol + D12 order.
# New file (unregistered harness, not sealed). Uses the uv prefix (OPUS-RULES).
R=artifacts/claude-mouth241b-20260922/runs
CF=artifacts/claude-determinism228-20260922/loop228-config.json
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
for k in 1 2 3; do
  for ag in 228 241b; do
    uptime
    if [ $ag = 228 ]; then AG=scripts/claude_loop228_agent.py; ML=""; SC=""; else AG=scripts/claude_loop241b_agent.py; ML="--mouthlog $R/mouth241b-run$k.log"; SC="--scorer241b"; fi
    t0=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
    uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/claude_mouth241b_suites.py --capture $R/cap$ag-run$k $ML $SC -- --agent $AG --config $CF --base 138i --only rt136,rt143,sessions152,bench --out $R/out$ag-run$k > $R/suites-$ag-run$k.log 2>&1
    rc=$?
    t1=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
    echo "WALL agent=$ag run=$k rc=$rc seconds=$(perl -e "printf q(%.1f), $t1-$t0")" | tee -a $R/walls.txt
  done
done
for ag in 228 241b; do
  uptime
  if [ $ag = 228 ]; then AG=scripts/claude_loop228_agent.py; else AG=scripts/claude_loop241b_agent.py; fi
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_sleepsmoke206.py --agent $AG --config $CF --root $R/sleep-$ag --report $R/sleep-$ag.json --label $ag > $R/sleep-$ag.log 2>&1
  echo "SLEEP $ag rc=$?" | tee -a $R/walls.txt
done
echo ALLDONE
