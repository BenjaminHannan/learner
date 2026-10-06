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
print("SEAL OK")
P
export HF_HUB_DISABLE_PROGRESS_BARS=1
python3 -c "from huggingface_hub import snapshot_download as s; print('LM at', s('LiquidAI/LFM2.5-1.2B-Instruct'))"
for S in 0 1; do
  python3 train.py --arm B --seed $S --steps 3000 --out results > run-B$S.out 2>&1 &
  python3 train.py --arm B --copy --seed $S --steps 3000 --out results > run-Bcopy$S.out 2>&1 &
done
while pgrep -f "train.py --arm" >/dev/null; do for f in run-*.out; do echo "$f: $(grep -E '^step' $f | tail -1 | cut -c1-200)"; done; sleep 60; done
for f in run-*.out; do echo "=== $f"; grep -E "Traceback|Error" $f; grep -E "^RESULT-JSON" $f | cut -c1-300; grep -E "^ROW " $f | cut -c1-260; done
echo ALL-DONE
