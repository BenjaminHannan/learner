#!/bin/bash
# Test SCM2 (roadmap after a6fa5a931b): two nights at SCM's recipe vs W1 then W2, both parents, then the report.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
for p in s100 s101; do
  (python3 -m creative.night7d scm2 --nprime ~/c7d/$p/Nprime.pt --s1 ~/c7d/s1 --s3 ~/c7d/s3 --r ~/c7d/r --j ~/c7d/j --l2 ~/c7d/l2 --scm ~/c7d/scm --s1w ~/c7d/s1w --out ~/c7d/scm2 --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --b2 ~/fs/B2_$p.pt --threads 2 >> ~/c7d/scm2-$p.log 2>&1; echo "SCM2 $p $?" >> ~/c7d/chain19.txt) &
done
wait
python3 -m creative.night7d scm2report --out ~/c7d/scm2 --parents s100 s101 > ~/c7d/scm2-report.log 2>&1; echo "SCM2REPORT $?" >> ~/c7d/chain19.txt
