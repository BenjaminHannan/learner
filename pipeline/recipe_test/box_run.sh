#!/bin/bash
# Runs on the rented vast box. JOBS="pool-old:0 copy-mix:3 ..." (arm:seed). 3 runs in parallel per wave.
exec > >(tee -a /workspace/box.log) 2>&1
date -u
cd /workspace/bundle || exit 1
export PYTHONPATH=/workspace/bundle:/workspace/bundle/scripts:/workspace/bundle/scripts/cap256_launch:/workspace/bundle/recipe_test
export HF_HUB_DISABLE_PROGRESS_BARS=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
python3 -c "import torch;print('torch',torch.__version__,torch.cuda.is_available())"
pip install -q -U transformers accelerate 'huggingface-hub<1.0' 2>&1 | tail -1
python3 -c "
from huggingface_hub import snapshot_download as s
print('LM at', s('LiquidAI/LFM2.5-1.2B-Instruct', revision='0f604ada3f766f9f257460c4c9f0b5d6f69d431b', local_dir='/workspace/lfm'))"
mkdir -p /workspace/results
flags() { case $1 in pool-old) echo "";; copy-mix) echo "--copy --wording mix";; copy-old) echo "--copy";; pool-mix) echo "--wording mix";; esac; }
emit() { # emit <wave-number>: print the wave's result files as base64 with sha256s
  cd /workspace/results
  tar czf /workspace/wave$1.tgz *.json 2>/dev/null
  echo "BEGIN-B64 wave$1.tgz $(sha256sum /workspace/wave$1.tgz | cut -d' ' -f1) $(stat -c %s /workspace/wave$1.tgz)"
  base64 -w 380 /workspace/wave$1.tgz | awk '{print "B64 " NR " " $0}'
  echo "END-B64 wave$1.tgz"
  (sha256sum *.json; echo MANIFEST-END) | sed 's/^/MANIFEST /'
  cd /workspace/bundle
}
set -- $JOBS
W=0
while [ $# -gt 0 ]; do
  W=$((W+1)); PIDS=""
  for k in 1 2 3; do
    [ $# -eq 0 ] && break
    arm=${1%%:*}; seed=${1##*:}; shift
    python3 recipe_test/run_arm.py --seed $seed $(flags $arm) --lm /workspace/lfm --out /workspace/results > /workspace/run-$arm-$seed.out 2>&1 &
    PIDS="$PIDS $!"
  done
  while kill -0 $(echo $PIDS | cut -d' ' -f1) 2>/dev/null || pgrep -f run_arm.py >/dev/null; do
    for f in /workspace/run-*.out; do echo "$(basename $f): $(grep -E '^step|Error|Traceback' $f | tail -1 | cut -c1-200)"; done; sleep 90
  done
  for f in /workspace/run-*.out; do grep -E "Traceback|Error" $f | head -3; done
  emit $W
done
echo ALL-DONE
date -u
