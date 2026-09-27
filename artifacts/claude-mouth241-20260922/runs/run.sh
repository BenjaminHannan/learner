#!/bin/bash
# exp 241 registered runs (post-seal). D6 wall protocol + D12 order.
R=/private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/reg241b
CF=artifacts/claude-determinism228-20260922/loop228-config.json
for k in 1 2 3; do
  for ag in 228 241; do
    uptime
    if [ $ag = 228 ]; then AG=scripts/claude_loop228_agent.py; ML=""; else AG=scripts/claude_loop241_agent.py; ML="--mouthlog $R/mouth241-run$k.log"; fi
    t0=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
    /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/u scripts/claude_mouth241_suites.py --capture $R/cap$ag-run$k $ML -- --agent $AG --config $CF --base 138i --only rt136,rt143,sessions152,bench --out $R/out$ag-run$k > $R/suites-$ag-run$k.log 2>&1
    rc=$?
    t1=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
    echo "WALL agent=$ag run=$k rc=$rc seconds=$(perl -e "printf q(%.1f), $t1-$t0")" | tee -a $R/walls.txt
  done
done
for ag in 228 241; do
  uptime
  /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/u scripts/fable_sleepsmoke206.py --agent scripts/claude_loop${ag}_agent.py --config $CF --root $R/sleep-$ag --report $R/sleep-$ag.json --label $ag > $R/sleep-$ag.log 2>&1
  echo "SLEEP $ag rc=$?" | tee -a $R/walls.txt
done
echo ALLDONE
