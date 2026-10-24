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

if [ -n "${BIG:-}" ] && [ ! -f "$OUT/.installed" ]; then   # big-model reference: vLLM brings its own torch
  python3 -m pip install -q "vllm==${VLLM:-0.32.0}" && touch "$OUT/.installed"
fi
if [ ! -f "$OUT/.installed" ]; then
  python3 -c "import torch" 2>/dev/null || python3 -m pip install torch
  TV=$(python3 -c "import torch;print(torch.__version__.split('+')[0])"); echo "torch==$TV" > /tmp/torch-pin.txt
  python3 -m pip install -q -r backbone/requirements.txt -c /tmp/torch-pin.txt
  if [ "${WITH_CONV1D:-0}" = 1 ]; then python3 -m pip install ninja packaging && python3 -m pip install causal-conv1d --no-build-isolation || echo "causal-conv1d build failed; using torch fallback"; fi
  touch "$OUT/.installed"
fi
[ -n "${BIG:-}" ] || python3 - <<'PY'
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

if [ -n "${SLEEP_ARMS:-}" ]; then   # Sleep-1 experiment (backbone/PREREG-sleep1.md): skips the village data build and arms
  for a in ${SLEEP_ARMS//,/ }; do
    if [ -f "$OUT/sleep/$a/result_$a.json" ]; then echo "-- skip sleep $a"; continue; fi
    echo "-- sleep $a $(date -u +%T)"
    python3 backbone/sleep/sleep1.py --arm "$a" --model "${SLEEP_MODEL:-Qwen/Qwen3.5-2B}" --out "$OUT/sleep/$a" || echo "!! sleep $a failed"
  done
  tar czf out.tar.gz --exclude="$OUT/.installed" "$OUT" || [ $? -eq 1 ]
  ls -la out.tar.gz; echo "== done $(date -u +%FT%TZ)"; exit 0
fi

if [ -n "${CREATIVE_ARMS:-}" ]; then   # Creative-1 experiment (backbone/PREREG-creative1.md): arms f0,c16,sleep in that order
  for a in ${CREATIVE_ARMS//,/ }; do
    if [ -f "$OUT/creative/$a/result_$a.json" ]; then echo "-- skip creative $a"; continue; fi
    echo "-- creative $a $(date -u +%T)"
    python3 backbone/creative/creative1.py --arm "$a" --model "${CREATIVE_MODEL:-Qwen/Qwen3.5-0.8B}" --out "$OUT/creative/$a" ${CREATIVE_FLAGS:-} || echo "!! creative $a failed"
  done
  tar czf out.tar.gz --exclude="$OUT/.installed" "$OUT" || [ $? -eq 1 ]
  ls -la out.tar.gz; echo "== done $(date -u +%FT%TZ)"; exit 0
fi

if [ -n "${LEAP_ARMS:-}${LEAP_REFS:-}${LEAP_VLLM_REFS:-}" ]; then   # Leap-1 experiment (backbone/PREREG-leap1.md). LEAP_ARMS="leap:0,self:0" (arm:seed), LEAP_REFS="Qwen/Qwen3.5-4B,..." (HF), LEAP_VLLM_REFS="Qwen/Qwen3.6-35B-A3B" (needs BIG=1 box)
  for r in $(echo "${LEAP_REFS:-}" | tr , " "); do
    n=${r##*/}
    if [ -f "$OUT/leap/result_ref_$n.json" ]; then echo "-- skip leap ref $n"; continue; fi
    echo "-- leap ref $n $(date -u +%T)"
    python3 backbone/leap/leap1.py --arm ref --c16 --model "$r" --out "$OUT/leap/ref_$n" && cp "$OUT/leap/ref_$n/result_ref_s0.json" "$OUT/leap/result_ref_$n.json" || echo "!! leap ref $n failed"
  done
  for r in $(echo "${LEAP_VLLM_REFS:-}" | tr , " "); do
    n=${r##*/}
    if [ -f "$OUT/leap/vllm/result_ref_$n.json" ]; then echo "-- skip leap vllm ref $n"; continue; fi
    python3 backbone/leap/ref_vllm.py --model "$r" --c16 --out "$OUT/leap/vllm" || echo "!! leap vllm ref $n failed"
  done
  for a in $(echo "${LEAP_ARMS:-}" | tr , " "); do
    arm=${a%%:*}; sd=${a##*:}
    if [ -f "$OUT/leap/$arm/result_${arm}_s$sd.json" ] && python3 -c "import json,sys;sys.exit(0 if len(json.load(open('$OUT/leap/$arm/result_${arm}_s$sd.json'))['rounds'])>=${LEAP_ROUNDS:-5}+1 else 1)"; then echo "-- skip leap $arm s$sd"; continue; fi
    echo "-- leap $arm s$sd $(date -u +%T)"
    python3 backbone/leap/leap1.py --arm "$arm" --seed "$sd" --rounds "${LEAP_ROUNDS:-5}" --model "${LEAP_MODEL:-Qwen/Qwen3.5-0.8B}" --out "$OUT/leap/$arm" || echo "!! leap $arm s$sd failed"
  done
  tar czf out.tar.gz --exclude="$OUT/.installed" "$OUT" || [ $? -eq 1 ]
  ls -la out.tar.gz; echo "== done $(date -u +%FT%TZ)"; exit 0
fi

DATA=$OUT/data
[ -f "$DATA/DATA_REPORT.json" ] || python3 backbone/build_data.py "$DATA" --workers "$(nproc)"

EXTRA=""
if [ -n "${PROBES:-}" ]; then   # generalization probes (one axis switched; generator from the generalization thread, seed 101)
  if [ ! -f "$DATA/probes.done" ]; then
    (cd backbone/genlab && mkdir -p data/village && cp -r ../../data/village/patterns data/village/ && \
     python3 -m generalize.probes ../../$OUT/probes_raw --visits ${PROBE_VISITS:-500} --probes "$PROBES" --workers "$(nproc)") && \
    python3 backbone/probe_rows.py $OUT/probes_raw $DATA && touch "$DATA/probes.done"
  fi
  for p in ${PROBES//,/ }; do EXTRA="$EXTRA --extra-eval $p=$DATA/probe_$p.jsonl"; done
fi
COMMON="$EXTRA --seed ${SEED:-0} --data $DATA --steps $STEPS --bsz $BSZ --micro-bsz $MICRO --max-len $MAXLEN"
step() {  # step NAME RESULT_FILE args...
  local name=$1 res=$2; shift 2
  if [ -f "$res" ]; then echo "-- skip $name (have $res)"; return; fi
  echo "-- $name $(date -u +%T)"; python3 backbone/train.py "$@" || echo "!! $name failed"
}
if [ -n "${BIG:-}" ]; then
  [ -f $OUT/big/result_big.json ] || python3 backbone/eval_vllm.py --model "$BIG" --data $DATA --out $OUT/big --max-len ${BIGLEN:-4096} || echo "!! big failed"
  ARMS=${ARMS:-none}
fi
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
