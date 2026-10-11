#!/bin/bash
# Test APM (roadmap after 03be030d3b): SCM2's night 2 drawing records from both nights, both parents, then the report.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
for p in s100 s101; do
  (python3 -m creative.night7d apm --nprime ~/c7d/$p/Nprime.pt --s1 ~/c7d/s1 --s3 ~/c7d/s3 --r ~/c7d/r --j ~/c7d/j --scm ~/c7d/scm --scm2 ~/c7d/scm2 --out ~/c7d/apm --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --b2 ~/fs/B2_$p.pt --threads 2 >> ~/c7d/apm-$p.log 2>&1; echo "APM $p $?" >> ~/c7d/chain20.txt) &
done
wait
python3 -m creative.night7d apmreport --out ~/c7d/apm --parents s100 s101 > ~/c7d/apm-report.log 2>&1; echo "APMREPORT $?" >> ~/c7d/chain20.txt
