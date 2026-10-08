#!/bin/bash
# Research-loop re-score with the new harm measure (roadmap e9e0bd2aeb), CPU fallback (Vast rental blocked): seeds 0, 1 (s200, s201) after VL.
cd /home/user/learner
export PYTHONPATH=/home/user/learner
until grep -q "VLREPORT" ~/c7d/chain10.txt 2>/dev/null; do sleep 30; done
for s in 0 1; do
  (python3 -m creative.rl.rescore_harm --seeds $s --b2-dir ~/fs/ckpt --out ~/c7d/rescore/seed$s --device cpu --threads 2 >> ~/c7d/rescore-seed$s.log 2>&1; echo "RESCORE $s $?" >> ~/c7d/chain11.txt) &
done
wait
echo "RESCOREDONE" >> ~/c7d/chain11.txt
