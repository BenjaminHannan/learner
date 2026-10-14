#!/bin/bash
export PYTHONPATH=/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt
cd /tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe
while pgrep -f "run_probe.py D1b3500" > /dev/null; do sleep 10; done
python3 item5.py D1b3500 > logs/item5.log 2>&1
python3 run_extra.py D1b3500 > logs/extra_D1b3500.log 2>&1
for t in parent D1b1500 L1000 P1000; do python3 run_probe.py $t > logs/$t.log 2>&1; python3 run_extra.py $t > logs/extra_$t.log 2>&1; done
for t in D1b2500 D1b3000 D1b2000 D1b1000 D1b500 D1_1500; do python3 run_probe.py $t > logs/$t.log 2>&1; done
echo ALLDONE > logs/master.done
