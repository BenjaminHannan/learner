#!/bin/bash
# HOLD (Ben 3:27 PM ET 10-08: no pile of little tests): only finish L64's report; SC, AP and the re-score are held.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
until grep -q "L64 s100" ~/c7d/chain13.txt 2>/dev/null && grep -q "L64 s101" ~/c7d/chain13.txt 2>/dev/null; do sleep 30; done
python3 -m creative.night7d l2report --visits 64 --out ~/c7d/l64 --parents s100 s101 > ~/c7d/l64-report.log 2>&1; echo "L64REPORT $?" >> ~/c7d/chain14.txt
