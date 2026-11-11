#!/bin/bash
# try the harness on the CPU against the dry-run workspace: prof_try.sh NAME ARGS...   (output in /dev/shm/ptcdry/ptry/NAME.*)
P=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad
J=/dev/shm/ptcdry/J
PY=$P/prof/prof_train.py
export PATH=/dev/shm/ptcdry/venv/bin:$PATH
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1 PYTHONUTF8=1
export CUSTOM_IO_EG2=$J/eg2
mkdir -p /dev/shm/ptcdry/ptry
nm=$1; shift
POOL=$J/work/g8a/pools/p10-rung30-s400-a64-L
s=$(date +%s)
timeout -k 10 1500 python $PY --data $POOL --pkg-root $J/src-ptc --out /dev/shm/ptcdry/ptry/$nm.json "$@" > /dev/shm/ptcdry/ptry/$nm.log 2>&1
echo "rc=$? secs=$(( $(date +%s) - s ))" >> /dev/shm/ptcdry/ptry/$nm.log
tail -n 5 /dev/shm/ptcdry/ptry/$nm.log | cut -c1-300
ls -la /dev/shm/ptcdry/ptry/ | grep "$nm" | cut -c1-200
