#!/bin/bash
# quick retry of ONLY the job command of the CPU dry run (after freeing /dev/shm), same command file and environment the box script used
# usage: rerun_job.sh LOG ; peak resident memory of the python processes is sampled every 5 s into LOG.rss
J=/dev/shm/ptcdry/J
export PATH=/dev/shm/ptcdry/venv/bin:$PATH
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1 PYTHONUTF8=1
export CUSTOM_IO_EG2=$J/eg2
. $J/state/env.sh
rm -rf $J/work/results/8aPTC3S-pc/8aPTC3S-3M-s400/PTC $J/work/results/8aPTC3S-pc/8aPTC3S-3M-s400/RESULT.json
mkdir -p $J/work/results/8aPTC3S-pc/8aPTC3S-3M-s400
date -u +%T > $1
bash $J/state/cmd.job.sh >> $1 2>&1 &
pid=$!
: > $1.rss
while kill -0 $pid 2>/dev/null; do
  ps -eo rss,args | grep 'custom_io\.' | grep -v grep | awk '{s+=$1} END {print s/1024}' >> $1.rss
  sleep 5
done
wait $pid
echo "rerun exit $?" >> $1
date -u +%T >> $1
sort -n $1.rss | tail -1 | sed 's/^/peak rss MiB of custom_io processes: /' >> $1
