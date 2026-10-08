#!/bin/bash
# 7d Test L2 (roadmap 7c8041caa3): both parents in parallel, joint report; then the research-loop re-score (seeds 0, 1) on CPU.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
for p in s100 s101; do
  (python3 -m creative.night7d l2 --nprime ~/c7d/$p/Nprime.pt --s3 ~/c7d/s3 --j ~/c7d/j --r ~/c7d/r --vl ~/c7d/vl --s1w ~/c7d/s1w --out ~/c7d/l2 --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --b2 ~/fs/B2_$p.pt --threads 2 >> ~/c7d/l2-$p.log 2>&1; echo "L2 $p $?" >> ~/c7d/chain12.txt) &
done
wait
python3 -m creative.night7d l2report --out ~/c7d/l2 --parents s100 s101 > ~/c7d/l2-report.log 2>&1; echo "L2REPORT $?" >> ~/c7d/chain12.txt
for s in 0 1; do
  (python3 -m creative.rl.rescore_harm --seeds $s --b2-dir ~/fs/ckpt --out ~/c7d/rescore/seed$s --device cpu --threads 2 >> ~/c7d/rescore-seed$s.log 2>&1; echo "RESCORE $s $?" >> ~/c7d/chain12.txt) &
done
wait
echo "RESCOREDONE" >> ~/c7d/chain12.txt
