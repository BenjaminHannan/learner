#!/bin/bash
exec > >(tee -a /workspace/box.log) 2>&1
cd /workspace/reasoner_fresh
pip install -q -U transformers accelerate 2>&1 | tail -1
python3 - <<'P'
import json,hashlib,subprocess
subprocess.run(["python3","seal.py"],check=True)
seal=json.load(open("SEAL.json"))
for f,h in seal["files"].items():
    assert hashlib.sha256(open(f,"rb").read()).hexdigest()==h,("SEAL MISMATCH",f)
s2=json.load(open("SEAL-v2.json"))
for f,h in s2.items():
    assert hashlib.sha256(open(f,"rb").read()).hexdigest()==h,("SEAL2 MISMATCH",f)
print("SEAL OK (v1 and v2)")
P
export HF_HUB_DISABLE_PROGRESS_BARS=1
python3 -c "from huggingface_hub import snapshot_download as s; print('LM at', s('LiquidAI/LFM2.5-1.2B-Instruct'))"
for S in 0 1 2 3 4 5; do
  python3 train.py --arm B --copy --wording mix --eval-form EVAL-FORM-v2.json --seed $S --steps 3000 --out results2 > run-M$S.out 2>&1 &
done
while pgrep -f "train.py --arm" >/dev/null; do for f in run-*.out; do echo "$f: $(grep -E '^step' $f | tail -1 | cut -c1-200)"; done; sleep 60; done
for f in run-*.out; do echo "=== $f"; grep -E "Traceback|Error" $f; grep -E "^ROW " $f | cut -c1-260; done
echo ALL-DONE
