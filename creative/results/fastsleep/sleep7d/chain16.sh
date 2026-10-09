#!/bin/bash
# Test SC (roadmap a92e5945fe; un-held by the big-run scorecard 10-09 step (c), Ben 10:43/10:57 AM ET 10-09: cheap free-compute tests for the principles), both parents, then the report.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
for p in s100 s101; do
  (python3 -m creative.night7d sc --nprime ~/c7d/$p/Nprime.pt --s1 ~/c7d/s1 --s3 ~/c7d/s3 --r ~/c7d/r --s1w ~/c7d/s1w --out ~/c7d/sc --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --b2 ~/fs/B2_$p.pt --threads 2 >> ~/c7d/sc-$p.log 2>&1; echo "SC $p $?" >> ~/c7d/chain16.txt) &
done
wait
python3 -m creative.night7d screport --out ~/c7d/sc --parents s100 s101 > ~/c7d/sc-report.log 2>&1; echo "SCREPORT $?" >> ~/c7d/chain16.txt
