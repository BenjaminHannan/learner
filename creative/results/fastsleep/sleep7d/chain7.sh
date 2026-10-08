#!/bin/bash
# 7d Test S1w (roadmap 7d 10-08): after R (all 4 cores), both parents in parallel, then the joint report.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
until grep -q "RREPORT" ~/c7d/chain6.txt 2>/dev/null; do sleep 30; done
for p in s100 s101; do
  (python3 -m creative.sleep7d s1w --nprime ~/c7d/$p/Nprime.pt --s1 ~/c7d/s1 --s3 ~/c7d/s3 --out ~/c7d/s1w --threads 2 >> ~/c7d/s1w-$p.log 2>&1; echo "S1W $p $?" >> ~/c7d/chain7.txt) &
done
wait
python3 -m creative.sleep7d s1wreport --out ~/c7d/s1w --parents s100 s101 > ~/c7d/s1w-report.log 2>&1; echo "S1WREPORT $?" >> ~/c7d/chain7.txt
