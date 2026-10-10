#!/bin/bash
# Test SCM (roadmap, 10-09: SCL at lr 3e-4), both parents, then the report.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
for p in s100 s101; do
  (python3 -m creative.night7d scm --nprime ~/c7d/$p/Nprime.pt --s1 ~/c7d/s1 --s3 ~/c7d/s3 --r ~/c7d/r --vl ~/c7d/vl --l2 ~/c7d/l2 --s1w ~/c7d/s1w --scl ~/c7d/scl --out ~/c7d/scm --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --b2 ~/fs/B2_$p.pt --threads 2 >> ~/c7d/scm-$p.log 2>&1; echo "SCM $p $?" >> ~/c7d/chain18.txt) &
done
wait
python3 -m creative.night7d scmreport --out ~/c7d/scm --parents s100 s101 > ~/c7d/scm-report.log 2>&1; echo "SCMREPORT $?" >> ~/c7d/chain18.txt
