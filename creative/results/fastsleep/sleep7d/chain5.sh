#!/bin/bash
# 7d Test J (roadmap 7d 10-08, a27faa485b): both parents in parallel, then the joint report.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
for p in s100 s101; do
  (python3 -m creative.sleep7d j --nprime ~/c7d/$p/Nprime.pt --out ~/c7d/j --s1 ~/c7d/s1 --s3 ~/c7d/s3 --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --b2 ~/fs/B2_$p.pt --threads 2 >> ~/c7d/j-$p.log 2>&1; echo "J $p $?" >> ~/c7d/chain5.txt) &
done
wait
python3 -m creative.sleep7d jreport --out ~/c7d/j --parents s100 s101 > ~/c7d/j-report.log 2>&1; echo "JREPORT $?" >> ~/c7d/chain5.txt
