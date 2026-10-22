#!/bin/bash
export PYTHONPATH=/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt
cd /tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe
while pgrep -f run_all.sh > /dev/null; do sleep 15; done
python3 item5.py D1b3500 > logs/item5.log 2>&1
for t in D1b3500 parent D1b1500 L1000 P1000; do python3 run_extra.py $t > logs/extra_$t.log 2>&1; done
