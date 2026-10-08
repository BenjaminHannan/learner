#!/bin/bash
# 7d Test R (roadmap e9e0bd2aeb): after J (needs J's W day 2 and W2), both parents in parallel, then the joint report.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
until grep -q "JREPORT" ~/c7d/chain5.txt 2>/dev/null; do sleep 30; done
for p in s100 s101; do
  (python3 -m creative.repair7d r --nprime ~/c7d/$p/Nprime.pt --j ~/c7d/j --s3 ~/c7d/s3 --out ~/c7d/r --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --threads 2 >> ~/c7d/r-$p.log 2>&1; echo "R $p $?" >> ~/c7d/chain6.txt) &
done
wait
python3 -m creative.repair7d rreport --out ~/c7d/r --parents s100 s101 > ~/c7d/r-report.log 2>&1; echo "RREPORT $?" >> ~/c7d/chain6.txt
