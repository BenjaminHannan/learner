#!/bin/bash
# 7d Test S1f (roadmap 377df3fc2c): after the 2x2 drift check, both parents in parallel, then the joint report.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
until grep -q "DRIFTREPORT" ~/c7d/chain8.txt 2>/dev/null; do sleep 30; done
for p in s100 s101; do
  (python3 -m creative.sleep7d s1f --nprime ~/c7d/$p/Nprime.pt --s1w ~/c7d/s1w --s3 ~/c7d/s3 --out ~/c7d/s1f --threads 2 >> ~/c7d/s1f-$p.log 2>&1; echo "S1F $p $?" >> ~/c7d/chain9.txt) &
done
wait
python3 -m creative.sleep7d s1freport --out ~/c7d/s1f --parents s100 s101 > ~/c7d/s1f-report.log 2>&1; echo "S1FREPORT $?" >> ~/c7d/chain9.txt
