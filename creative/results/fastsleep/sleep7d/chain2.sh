#!/bin/bash
# 7d chain 2 (roadmap ruling 13f4b987eb): S1 on both parents (parallel, 2 threads each), its verdict, then S3 reusing S1's days.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
for p in s100 s101; do
  (python3 -m creative.sleep7d s1 --nprime ~/c7d/$p/Nprime.pt --out ~/c7d/s1 --threads 2 >> ~/c7d/s1-$p.log 2>&1; echo "S1 $p $?" >> ~/c7d/chain2.txt) &
done
wait
python3 -m creative.sleep7d s1report --out ~/c7d/s1 --parents s100 s101 > ~/c7d/s1-report.log 2>&1; echo "S1REPORT $?" >> ~/c7d/chain2.txt
for p in s100 s101; do
  (python3 -m creative.sleep7d s3 --nprime ~/c7d/$p/Nprime.pt --out ~/c7d/s3 --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --day-from ~/c7d/s1 --threads 2 >> ~/c7d/s3-$p.log 2>&1; echo "S3 $p $?" >> ~/c7d/chain2.txt) &
done
wait
echo "CHAIN DONE" >> ~/c7d/chain2.txt
