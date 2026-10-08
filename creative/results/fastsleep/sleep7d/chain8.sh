#!/bin/bash
# 7d 2x2 drift check (roadmap 8e924aaa2f): after S1w, both parents in parallel from W1, then the joint report.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
until grep -q "S1WREPORT" ~/c7d/chain7.txt 2>/dev/null; do sleep 30; done
for p in s100 s101; do
  (python3 -m creative.drift7d run --model ~/c7d/s3/$p/W1.pt --out ~/c7d/drift --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --threads 2 >> ~/c7d/drift-$p.log 2>&1; echo "DRIFT $p $?" >> ~/c7d/chain8.txt) &
done
wait
python3 -m creative.drift7d report --out ~/c7d/drift --parents s100 s101 > ~/c7d/drift-report.log 2>&1; echo "DRIFTREPORT $?" >> ~/c7d/chain8.txt
