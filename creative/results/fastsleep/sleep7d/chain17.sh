#!/bin/bash
# Test SCL (roadmap e5ab95d650), both parents, then the report.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
for p in s100 s101; do
  (python3 -m creative.night7d scl --nprime ~/c7d/$p/Nprime.pt --s1 ~/c7d/s1 --s3 ~/c7d/s3 --r ~/c7d/r --vl ~/c7d/vl --l2 ~/c7d/l2 --s1w ~/c7d/s1w --out ~/c7d/scl --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --b2 ~/fs/B2_$p.pt --threads 2 >> ~/c7d/scl-$p.log 2>&1; echo "SCL $p $?" >> ~/c7d/chain17.txt) &
done
wait
python3 -m creative.night7d sclreport --out ~/c7d/scl --parents s100 s101 > ~/c7d/scl-report.log 2>&1; echo "SCLREPORT $?" >> ~/c7d/chain17.txt
