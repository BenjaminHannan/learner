#!/bin/bash
exec > >(tee -a /workspace/box.log) 2>&1
cd /workspace/reasoner_fresh
pip install -q -U transformers accelerate 2>&1 | tail -1
python3 seal.py
export HF_HUB_DISABLE_PROGRESS_BARS=1
python3 -c "from huggingface_hub import snapshot_download as s; print('LM at', s('LiquidAI/LFM2.5-1.2B-Instruct'))"
for S in 0 1 2 3 4 5; do python3 train2.py --seed $S --steps 3000 --varied --out results2 > run-$S.out 2>&1 & done
while pgrep -f "train2.py" >/dev/null; do for f in run-*.out; do echo "$f: $(grep -E '^step' $f | tail -1 | cut -c1-220)"; done; sleep 60; done
for f in run-*.out; do echo "=== $f"; grep -E "Traceback|Error" $f; grep -E "^ROW " $f | cut -c1-300; done
echo ALL-DONE
