#!/bin/bash
# 7d Test VL (roadmap 7526d614e5): after S1f, both parents in parallel, then the joint report.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
until grep -q "S1FREPORT" ~/c7d/chain9.txt 2>/dev/null; do sleep 30; done
for p in s100 s101; do
  (python3 -m creative.night7d run --nprime ~/c7d/$p/Nprime.pt --s1 ~/c7d/s1 --s3 ~/c7d/s3 --r ~/c7d/r --out ~/c7d/vl --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --threads 2 >> ~/c7d/vl-$p.log 2>&1; echo "VL $p $?" >> ~/c7d/chain10.txt) &
done
wait
python3 -m creative.night7d report --out ~/c7d/vl --parents s100 s101 > ~/c7d/vl-report.log 2>&1; echo "VLREPORT $?" >> ~/c7d/chain10.txt
