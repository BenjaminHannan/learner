#!/usr/bin/env bash
# Think-1 runs (backbone/think/PREREG.md) on a GPU box or Ben's PC. Run from the repo root:
#   THINK_JOBS=a:0,b:0,t:0 bash backbone/think/run_box.sh
# Each job is ARM:SEED. Arms a and b are stage 1's (backbone/train.py, unchanged); t and t1 are Think-1's
# (backbone/think/think1.py). Idempotent: a job whose result file exists is skipped. Results land in out/think/.
# Env: THINK_JOBS (required)  STEPS=418 BSZ=16 MICRO=4 MAXLEN=2048 MODEL=Qwen/Qwen3.5-0.8B THINK_FLAGS='' (extra flags for t, '+'-separated)
set -euo pipefail
cd "$(dirname "$0")/../.."
STEPS=${STEPS:-418}; BSZ=${BSZ:-16}; MICRO=${MICRO:-4}; MAXLEN=${MAXLEN:-2048}; MODEL=${MODEL:-Qwen/Qwen3.5-0.8B}
OUT=out; mkdir -p "$OUT/think"
[ -n "${THINK_JOBS:-}" ] || { echo "THINK_JOBS is empty"; exit 2; }
echo "== think run_box $(date -u +%FT%TZ) jobs=$THINK_JOBS steps=$STEPS bsz=$BSZ micro=$MICRO maxlen=$MAXLEN model=$MODEL"
DATA=$OUT/data
[ -f "$DATA/DATA_REPORT.json" ] || python3 backbone/build_data.py "$DATA" --workers "$(nproc)"
COMMON="--model $MODEL --data $DATA --steps $STEPS --bsz $BSZ --micro-bsz $MICRO --max-len $MAXLEN"
for job in ${THINK_JOBS//,/ }; do
  arm=${job%%:*}; s=${job#*:}; d="$OUT/think/${arm}_s${s}"
  res="$d/result_${arm}_s${s}.json"
  if [ -f "$res" ]; then echo "-- skip $arm seed $s (have $res)"; continue; fi
  echo "-- $arm seed $s $(date -u +%T)"
  case "$arm" in
    a)  python3 backbone/train.py --arm a $COMMON --seed "$s" --out "$d" && mv "$d/result_a.json" "$res" || echo "!! a seed $s failed" ;;
    b)  python3 backbone/train.py --arm b $COMMON --seed "$s" --out "$d" && \
        python3 backbone/train.py --arm b $COMMON --seed "$s" --out "$d" --eval-loops 1 --load-adapter "$d/adapter" && \
        mv "$d/result_b_eval1.json" "$d/result_b1_s${s}.json" && mv "$d/result_b.json" "$res" || echo "!! b seed $s failed" ;;
    t|t1) python3 backbone/think/think1.py --arm "$arm" $COMMON --seed "$s" --out "$d" ${THINK_FLAGS//+/ } || echo "!! $arm seed $s failed" ;;
    *)  echo "!! unknown arm $arm" ;;
  esac
done
python3 backbone/think/summarize.py "$OUT/think" > "$OUT/think/SUMMARY.txt" 2>&1 || echo "!! summarize failed"
cat "$OUT/think/SUMMARY.txt" || true
cp "$DATA/DATA_REPORT.json" "$OUT/DATA_REPORT.json" 2>/dev/null || true
tar czf out.tar.gz --exclude="$OUT/data" --exclude="$OUT/.installed" --exclude='*/adapter/*' --exclude='*/think_block.pt' "$OUT" || [ $? -eq 1 ]
tar czf ckpt.tar.gz $(find "$OUT/think" \( -name adapter -o -name think_block.pt \) 2>/dev/null) 2>/dev/null || true   # weights, kept apart
ls -la out.tar.gz ckpt.tar.gz 2>/dev/null || true
echo "== think done $(date -u +%FT%TZ)"
