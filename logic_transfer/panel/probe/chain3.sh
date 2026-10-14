#!/bin/bash
export PYTHONPATH=/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt
cd /tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe
while [ ! -f logs/master.done ]; do sleep 20; done
for t in D1b3500 parent D1b1500 L1000 P1000; do python3 run_extra2.py $t > logs/extra2_$t.log 2>&1; done
echo done > logs/chain3.done
