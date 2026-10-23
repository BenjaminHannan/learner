#!/usr/bin/env bash
# Stage-1 run on the rented GPU box. Run from the repo root:  bash backbone/run_box.sh
# Idempotent: finished steps (result files) are skipped. Everything lands under out/; out.tar.gz at the end.
# Env: STEPS=3000 BSZ=16 MICRO=4 MAXLEN=1024 RUN_A2=0 WITH_CONV1D=0 MODEL=Qwen/Qwen3.5-0.8B MODEL2=Qwen/Qwen3.5-2B
set -euo pipefail
cd "$(dirname "$0")/.."
STEPS=${STEPS:-3000}; BSZ=${BSZ:-16}; MICRO=${MICRO:-4}; MAXLEN=${MAXLEN:-1024}
MODEL=${MODEL:-Qwen/Qwen3.5-0.8B}; MODEL2=${MODEL2:-Qwen/Qwen3.5-2B}
OUT=out; mkdir -p "$OUT"
exec > >(tee -a "$OUT/run_box.log") 2>&1
echo "== run_box $(date -u +%FT%TZ) steps=$STEPS bsz=$BSZ micro=$MICRO maxlen=$MAXLEN"
nvidia-smi --query-gpu=name,memory.total --format=csv || echo "no nvidia-smi"

if [ ! -f "$OUT/.installed" ]; then
  python3 -c "import torch" 2>/dev/null || python3 -m pip install torch
  TV=$(python3 -c "import torch;print(torch.__version__.split('+')[0])"); echo "torch==$TV" > /tmp/torch-pin.txt
  python3 -m pip install -q -r backbone/requirements.txt -c /tmp/torch-pin.txt
  if [ "${WITH_CONV1D:-0}" = 1 ]; then python3 -m pip install ninja packaging && python3 -m pip install causal-conv1d --no-build-isolation || echo "causal-conv1d build failed; using torch fallback"; fi
  touch "$OUT/.installed"
fi
python3 - <<'PY'
import torch, transformers, peft
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), "transformers", transformers.__version__, "peft", peft.__version__)
try:
    import fla; print("fla", fla.__version__)
except Exception as e: print("fla MISSING:", e)
try:
    import causal_conv1d; print("causal_conv1d ok")
except Exception as e: print("causal_conv1d missing (torch fallback):", type(e).__name__)
assert torch.cuda.is_available(), "no CUDA"
PY

DATA=$OUT/data
[ -f "$DATA/DATA_REPORT.json" ] || python3 backbone/build_data.py "$DATA" --workers "$(nproc)"

COMMON="--data $DATA --steps $STEPS --bsz $BSZ --micro-bsz $MICRO --max-len $MAXLEN"
step() {  # step NAME RESULT_FILE args...
  local name=$1 res=$2; shift 2
  if [ -f "$res" ]; then echo "-- skip $name (have $res)"; return; fi
  echo "-- $name $(date -u +%T)"; python3 backbone/train.py "$@" || echo "!! $name failed"
}
ARMS=${ARMS:-a0,a,b}
has() { case ",$ARMS," in *",$1,"*) return 0;; *) return 1;; esac; }
has a0 && step a0   $OUT/a0/result_a0.json   --arm a0 --model "$MODEL" $COMMON --out $OUT/a0
has a  && step a    $OUT/a/result_a.json     --arm a   --model "$MODEL" $COMMON --out $OUT/a
has b  && step b    $OUT/b/result_b.json     --arm b   --model "$MODEL" $COMMON --out $OUT/b
if has b && [ -d $OUT/b/adapter ]; then
  step b_lesion $OUT/b/result_b_eval1.json --arm b --model "$MODEL" $COMMON --out $OUT/b --eval-loops 1 --load-adapter $OUT/b/adapter
fi
if [ "${RUN_A2:-0}" = 1 ] || has a2; then
  step a2 $OUT/a2/result_a.json --arm a --model "$MODEL2" $COMMON --out $OUT/a2 --tag a2
fi
cp "$DATA/DATA_REPORT.json" "$OUT/DATA_REPORT.json" 2>/dev/null || true
tar czf out.tar.gz --exclude="$OUT/data" --exclude="$OUT/.installed" "$OUT" || [ $? -eq 1 ]  # exit 1 = a log file grew while archiving
ls -la out.tar.gz
echo "== done $(date -u +%FT%TZ)"
