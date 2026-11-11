#!/bin/bash
# is test_ptc flaky? run it N times on the tree of the failed dry run, full output kept per run
J=/dev/shm/ptcdry/J
export PATH=/dev/shm/ptcdry/venv/bin:$PATH
OUT=$1; N=$2
mkdir -p $OUT
cd $J/src-ptc || exit 1
for i in $(seq 1 $N); do
  env CUDA_VISIBLE_DEVICES=-1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1 PYTHONPATH=$J/src-ptc PTC_ORIG_TREE=$J/base python -m custom_io.tests.test_ptc > $OUT/run$i.log 2>&1
  echo "run $i exit $? $(date -u +%T) lines $(wc -l < $OUT/run$i.log)"
done
