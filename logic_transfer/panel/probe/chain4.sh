#!/bin/bash
export PYTHONPATH=/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt
cd /tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe
while [ ! -f logs/chain3.done ]; do sleep 10; done
for t in L1000 P1000; do python3 check_repro.py $t > logs/repro_$t.log 2>&1; done
echo done > logs/chain4.done
