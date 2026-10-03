#!/bin/bash
# Runs on the rented box. Probe two LRs on arm A (seed 9, no eval-form scoring), pick by train fit, run 4 main jobs.
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
nvidia-smi --query-gpu=name,memory.total --format=csv
export HF_HUB_DISABLE_PROGRESS_BARS=1
PSTEPS=${PSTEPS:-800}
python3 -c "from huggingface_hub import snapshot_download as s; print('LM at', s('LiquidAI/LFM2.5-1.2B-Instruct'))"
for LR in 1e-3 3e-4; do python3 train.py --arm A --seed 9 --steps $PSTEPS --lr $LR --probe --out probe-$LR > probe-$LR.out 2>&1 & done
while pgrep -f "train.py --arm" >/dev/null; do for f in probe-*.out; do echo "$f: $(tail -c 300 $f | tr '\r' '\n' | tail -2 | tr '\n' ' ')"; done; sleep 30; done
grep -h PROBE probe-*.out
BEST=$(python3 - <<'P'
import re,glob
best=None
for f in ["probe-1e-3.out","probe-3e-4.out"]:
    m=re.search(r"PROBE .* lr ([\d.e-]+) trainfit192 final ([\d.]+)",open(f).read())
    if m:
        lr,acc=m.group(1),float(m.group(2))
        if best is None or acc>best[1]+0.02: best=(lr,acc)
print(best[0] if best else "1e-3")
P
)
echo "CHOSEN LR $BEST"
for A in A B; do for S in 0 1; do python3 train.py --arm $A --seed $S --lr $BEST --steps ${STEPS:-3000} --out results > run-$A$S.out 2>&1 & done; done
while pgrep -f "train.py --arm" >/dev/null; do for f in run-*.out; do echo "$f: $(grep -E '^step' $f | tail -1)"; done; sleep 60; done
for f in run-*.out; do echo "=== $f"; grep -E "RESULT-JSON|ROWS-B64|Traceback|Error" $f; tail -3 $f; done
echo ALL-DONE
