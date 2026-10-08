#!/bin/bash
# 7d S3' (roadmap 36d3fc2d14): after S1b, P unchanged, control Z' = W1's own previous-night records at the same dose; W1 reused from S3.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
until grep -q "S1B VERDICT" ~/c7d/chain3.txt 2>/dev/null; do sleep 30; done
for p in s100 s101; do
  (python3 -m creative.sleep7d s3 --nprime ~/c7d/$p/Nprime.pt --out ~/c7d/s3p --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --day-from ~/c7d/s1 --w1-from ~/c7d/s3 --control w1 --threads 2 >> ~/c7d/s3p-$p.log 2>&1; echo "S3P $p $?" >> ~/c7d/chain4.txt) &
done
wait
echo "CHAIN4 DONE" >> ~/c7d/chain4.txt
