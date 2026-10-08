#!/bin/bash
# 7d S1b (roadmap 083303c493): after chain2 (S3) is done, F = C for tries 1-32 then U, both parents in parallel, then the combined verdict from the cached tries.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
until grep -q "CHAIN DONE" ~/c7d/chain2.txt 2>/dev/null; do sleep 30; done
for p in s100 s101; do
  (python3 -m creative.sleep7d s1b --nprime ~/c7d/$p/Nprime.pt --s1 ~/c7d/s1 --out ~/c7d/s1b --threads 2 >> ~/c7d/s1b-$p.log 2>&1; echo "S1B $p $?" >> ~/c7d/chain3.txt) &
done
wait
python3 -m creative.sleep7d s1b --nprime ~/c7d/s100/Nprime.pt ~/c7d/s101/Nprime.pt --s1 ~/c7d/s1 --out ~/c7d/s1b --threads 4 > ~/c7d/s1b-verdict.log 2>&1; echo "S1B VERDICT $?" >> ~/c7d/chain3.txt
