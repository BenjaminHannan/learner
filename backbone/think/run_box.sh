#!/usr/bin/env bash
# Think-1 runs (backbone/think/PREREG.md) on a GPU box or Ben's PC. Run from the repo root:
#   THINK_JOBS=a:0,b:0,aplus:0,t:0,t1:0 bash backbone/think/run_box.sh
# Each job is ARM:SEED with ARM in a b aplus bplus t t1 tw. EVERY arm runs backbone/think/think1.py (never backbone/train.py); the step
# counts are think1.py's per-arm defaults (418 stage 1, 1,254 stage 2), so there is no STEPS here.
# aplus, t, t1, tw need out/think/a_s{S}/adapter and bplus needs out/think/b_s{S}/adapter. If it is missing, that stage-1 arm runs first,
# in the same box (a result file without its adapter is deleted and retrained, so result and adapter always match).
# Idempotent: a job whose result file exists is skipped (a gate-aborted run also leaves a result: delete it to run again).
# Results land in out/think/{arm}_s{S}/result_{arm}_s{S}.json; out/think/SUMMARY.txt is the PREREG report.
# Env: THINK_JOBS (required)  BSZ=16 MICRO=4 MAXLEN=2048 MODEL=Qwen/Qwen3.5-0.8B  THINK_FLAGS='' (extra think1.py flags, '+'-separated)
#      PYTHON=python3  OUT=out  TARBALL=1 (0 skips the out.tar.gz / ckpt.tar.gz step)
set -euo pipefail
cd "$(dirname "$0")/../.."
BSZ=${BSZ:-16}; MICRO=${MICRO:-4}; MAXLEN=${MAXLEN:-2048}; MODEL=${MODEL:-Qwen/Qwen3.5-0.8B}
PYTHON=${PYTHON:-python3}; OUT=${OUT:-out}; mkdir -p "$OUT/think"
[ -n "${THINK_JOBS:-}" ] || { echo "THINK_JOBS is empty"; exit 2; }
echo "== think run_box $(date -u +%FT%TZ) jobs=$THINK_JOBS bsz=$BSZ micro=$MICRO maxlen=$MAXLEN model=$MODEL"
DATA=$OUT/data
[ -f "$DATA/DATA_REPORT.json" ] || $PYTHON backbone/build_data.py "$DATA" --workers "$(nproc)"
COMMON="--model $MODEL --data $DATA --bsz $BSZ --micro-bsz $MICRO --max-len $MAXLEN"

run_job() {   # ARM SEED: one think1.py run unless its result exists; non-zero if the run failed (exit 3 = mechanics gate abort)
  local arm=$1 s=$2 d="$OUT/think/${1}_s${2}"
  if [ -f "$d/result_${arm}_s${s}.json" ]; then echo "-- skip $arm seed $s (have result)"; return 0; fi
  echo "-- $arm seed $s $(date -u +%T)"
  $PYTHON backbone/think/think1.py --arm "$arm" $COMMON --seed "$s" --out "$d" ${THINK_FLAGS:+${THINK_FLAGS//+/ }} || { echo "!! $arm seed $s failed (rc=$?)"; return 1; }
}
need() {      # ARM SEED: succeeds once out/think/{ARM}_s{SEED}/adapter exists, training that stage-1 arm first if it does not
  local d="$OUT/think/${1}_s${2}"
  [ -f "$d/adapter/adapter_config.json" ] && return 0
  echo "-- need ${1} seed ${2} adapter: running it first"
  rm -f "$d/result_${1}_s${2}.json"
  run_job "$1" "$2" && [ -f "$d/adapter/adapter_config.json" ]
}
for job in ${THINK_JOBS//,/ }; do
  arm=${job%%:*}; s=${job#*:}
  case "$arm" in
    a|b)            run_job "$arm" "$s" || true ;;
    aplus|t|t1|tw)  if need a "$s"; then run_job "$arm" "$s" || true; else echo "!! $arm seed $s skipped: no a adapter"; fi ;;
    bplus)          if need b "$s"; then run_job "$arm" "$s" || true; else echo "!! $arm seed $s skipped: no b adapter"; fi ;;
    *)              echo "!! unknown arm $arm" ;;
  esac
done
$PYTHON backbone/think/summarize.py "$OUT/think" --data "$DATA" > "$OUT/think/SUMMARY.txt" 2>&1 || echo "!! summarize failed"
cat "$OUT/think/SUMMARY.txt" || true
cp "$DATA/DATA_REPORT.json" "$OUT/DATA_REPORT.json" 2>/dev/null || true
if [ "${TARBALL:-1}" = 1 ]; then
  tar czf out.tar.gz --exclude="$OUT/data" --exclude="$OUT/.installed" --exclude='*/adapter/*' --exclude='*/think_block.pt' "$OUT" || [ $? -eq 1 ]
  tar czf ckpt.tar.gz $(find "$OUT/think" \( -name adapter -o -name think_block.pt \) 2>/dev/null) 2>/dev/null || true   # weights, kept apart
  ls -la out.tar.gz ckpt.tar.gz 2>/dev/null || true
fi
echo "== think done $(date -u +%FT%TZ)"
