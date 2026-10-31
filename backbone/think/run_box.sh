#!/usr/bin/env bash
# Think-1 runs (backbone/think/PREREG.md) on a GPU box or Ben's PC. Run from the repo root:
#   THINK_JOBS=a:0,b:0,aplus:0,t:0,t1:0 bash backbone/think/run_box.sh
# Each job is ARM:SEED with ARM in a b aplus bplus t t1 tw tj tf tc ws wsham tsd tsd1 br aplong. EVERY arm runs backbone/think/think1.py (never backbone/train.py); the step
# counts are think1.py's per-arm defaults (418 stage 1, 1,254 stage 2), so there is no STEPS here.
# aplus, t, t1, tw, tj, tf, tc, ws, wsham, tsd, tsd1, br, aplong need out/think/a_s{S}/adapter and bplus needs out/think/b_s{S}/adapter. If it is missing, that stage-1 arm runs first,
# in the same box (a result file without its adapter is deleted and retrained, so result and adapter always match).
# Idempotent: a job whose result file exists is skipped (a gate-aborted run also leaves a result: delete it to run again).
# Results land in out/think/{arm}_s{S}/result_{arm}_s{S}.json; out/think/SUMMARY.txt is the PREREG report.
# ws, wsham, tsd, tsd1 first run backbone/think/preflight.py once (real model, bf16, CUDA; skipped with ALLOW_CPU=1); if it fails none of those jobs runs. Its output goes to $OUT/preflight, not $OUT/think.
# Env: THINK_JOBS (required)  BSZ=16 MICRO=4 MAXLEN=2048 MODEL=Qwen/Qwen3.5-0.8B  THINK_FLAGS='' (extra think1.py flags, '+'-separated)
#      PARALLEL=1 (jobs share the one GPU: all listed stage-1 jobs at once, then all stage-2 jobs at once, at most MAXPAR=3 processes at a time;
#      each job's output goes to out/think/{arm}_s{S}/run.log; a job with no result afterwards is rerun alone once; use MAXPAR=2 on a 24 GB card until a real run records peak_gpu_mem_gb; unset = one job after another, as above)  MAXPAR=3
#      PYTHON=python3  OUT=out  TARBALL=1 (0 skips the out.tar.gz / ckpt.tar.gz step)  ALLOW_CPU=1 (skip the CUDA check; CPU runs take days)
# Everything printed here is also appended to out/think/run.log. Without a CUDA GPU the script stops (exit 2): PREREG wants one GPU type per seed.
set -euo pipefail
cd "$(dirname "$0")/../.."
BSZ=${BSZ:-16}; MICRO=${MICRO:-4}; MAXLEN=${MAXLEN:-2048}; MODEL=${MODEL:-Qwen/Qwen3.5-0.8B}
PYTHON=${PYTHON:-python3}; OUT=${OUT:-out}; mkdir -p "$OUT/think"
exec > >(tee -a "$OUT/think/run.log") 2>&1
[ -n "${THINK_JOBS:-}" ] || { echo "THINK_JOBS is empty"; exit 2; }
if [ "${ALLOW_CPU:-0}" != 1 ]; then
  $PYTHON -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" || { echo "!! no CUDA GPU visible to $PYTHON (ALLOW_CPU=1 runs on the CPU anyway: days, and not the same hardware as the other arms)"; exit 2; }
fi
echo "== think run_box $(date -u +%FT%TZ) jobs=$THINK_JOBS bsz=$BSZ micro=$MICRO maxlen=$MAXLEN model=$MODEL"
DATA=$OUT/data
[ -f "$DATA/DATA_REPORT.json" ] || $PYTHON backbone/build_data.py "$DATA" --workers "$(nproc)"
COMMON="--model $MODEL --data $DATA --bsz $BSZ --micro-bsz $MICRO --max-len $MAXLEN"

preflight() { # SEED: real-model check before ws / wsham / tsd / tsd1 (20 steps of tsd and of ws, bf16, CUDA: dec-LoRA gradients, main-LoRA gradient unchanged by a zero step loss, adapter/dec saved, peak memory). Once per run.
  local ok="$OUT/preflight/ok" ai
  [ -f "$ok" ] && return 0
  [ "${ALLOW_CPU:-0}" = 1 ] && { echo "-- preflight skipped (ALLOW_CPU=1: no GPU)"; return 0; }
  need a "$1" || return 1
  ai=$(printf '%s' "${THINK_FLAGS:-}" | sed -n 's/.*--alpha-init+\([0-9.]*\).*/\1/p')
  echo "-- preflight seed $1 $(date -u +%T)"
  $PYTHON backbone/think/preflight.py --a-adapter "$OUT/think/a_s$1/adapter" --data "$DATA" --out "$OUT/preflight" --model "$MODEL" --seed "$1" --alpha-init "${ai:-0}" \
    && { mkdir -p "$OUT/preflight"; touch "$ok"; } || { echo "!! preflight failed: no ws / wsham / tsd / tsd1 job will run"; return 1; }
}
needs_pre() { case "$1" in ws|wsham|tsd|tsd1) return 0;; *) return 1;; esac; }

run_job() {   # ARM SEED: one think1.py run unless its result exists; non-zero if the run failed (exit 3 = mechanics gate abort)
  local arm=$1 s=$2 d="$OUT/think/${1}_s${2}"
  if [ -f "$d/result_${arm}_s${s}.json" ]; then echo "-- skip $arm seed $s (have result)"; return 0; fi
  if needs_pre "$arm"; then preflight "$s" || return 1; fi
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
par() {       # JOB...: run_job for each ARM:SEED in the background, never more than MAXPAR at a time; each job's output goes to its own run.log
  local job arm s d pids=()   # wait on the job pids, not bare `wait`: that would also wait for the tee of the exec > >(tee ...) above
  for job in "$@"; do
    arm=${job%%:*}; s=${job#*:}; d="$OUT/think/${arm}_s${s}"; mkdir -p "$d"
    while [ "$(jobs -rp | wc -l)" -ge "$MAXPAR" ]; do wait -n || true; done
    echo "-- start $arm seed $s $(date -u +%T) (log $d/run.log)"
    { ( run_job "$arm" "$s" ) >> "$d/run.log" 2>&1 && echo "-- done $arm seed $s $(date -u +%T)" || echo "!! $arm seed $s failed"; } &
    pids+=($!)
  done
  wait "${pids[@]}" || true
  for job in "$@"; do   # a job that died (typically out of GPU memory with the others alive) gets one more try alone: costs time, not the seed
    arm=${job%%:*}; s=${job#*:}; d="$OUT/think/${arm}_s${s}"
    [ -f "$d/result_${arm}_s${s}.json" ] && continue
    echo "-- retry $arm seed $s alone $(date -u +%T)"; run_job "$arm" "$s" >> "$d/run.log" 2>&1 || echo "!! $arm seed $s failed again"
  done
}
if [ "${PARALLEL:-0}" = 1 ]; then
  MAXPAR=${MAXPAR:-3}; s1=(); s2=()
  export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}   # less fragmentation: three evals at once are near 24 GB
  for job in ${THINK_JOBS//,/ }; do
    arm=${job%%:*}; s=${job#*:}
    case "$arm" in
      a|b)                    s1+=("$job");;
      aplus|t|t1|tw|tj|tf|tc|ws|wsham|tsd|tsd1|br|aplong|bplus)  s2+=("$job"); st=a; [ "$arm" = bplus ] && st=b
                              if [ ! -f "$OUT/think/${st}_s${s}/adapter/adapter_config.json" ]; then rm -f "$OUT/think/${st}_s${s}/result_${st}_s${s}.json"; s1+=("$st:$s"); fi;;
      *)                      echo "!! unknown arm $arm";;
    esac
  done
  mapfile -t s1 < <(printf '%s\n' "${s1[@]:-}" | awk 'NF && !seen[$0]++')   # stage 1 first, each arm once (a missing adapter's arm is added)
  echo "-- parallel: stage 1 (${s1[*]:-none}), maxpar $MAXPAR"
  [ ${#s1[@]} -eq 0 ] || par "${s1[@]}"
  ok=()
  for job in "${s2[@]:-}"; do
    [ -n "$job" ] || continue
    arm=${job%%:*}; s=${job#*:}; st=a; [ "$arm" = bplus ] && st=b
    # the adapter is saved before the stage-1 eval, so it exists even if that eval crashed: also need the stage-1 result, or a rerun retrains it under the dependents
    if [ -f "$OUT/think/${st}_s${s}/adapter/adapter_config.json" ] && [ -f "$OUT/think/${st}_s${s}/result_${st}_s${s}.json" ]; then ok+=("$job"); else echo "!! $arm seed $s skipped: $st seed $s did not finish"; fi
  done
  for job in "${ok[@]:-}"; do   # the preflight runs once, here, before the stage-2 processes start (run_job then finds its flag file)
    [ -n "$job" ] && needs_pre "${job%%:*}" && { preflight "${job#*:}" || { ok=($(printf '%s\n' "${ok[@]}" | grep -Ev '^(ws|wsham|tsd|tsd1):' || true)); }; break; }
  done
  echo "-- parallel: stage 2 (${ok[*]:-none}), maxpar $MAXPAR"
  [ ${#ok[@]} -eq 0 ] || par "${ok[@]}"
else
  for job in ${THINK_JOBS//,/ }; do
    arm=${job%%:*}; s=${job#*:}
    case "$arm" in
      a|b)            run_job "$arm" "$s" || true ;;
      aplus|t|t1|tw|tj|tf|tc|ws|wsham|tsd|tsd1|br|aplong)  if need a "$s"; then run_job "$arm" "$s" || true; else echo "!! $arm seed $s skipped: no a adapter"; fi ;;
      bplus)          if need b "$s"; then run_job "$arm" "$s" || true; else echo "!! $arm seed $s skipped: no b adapter"; fi ;;
      *)              echo "!! unknown arm $arm" ;;
    esac
  done
fi
$PYTHON backbone/think/summarize.py "$OUT/think" --data "$DATA" > "$OUT/think/SUMMARY.txt" 2>&1 || echo "!! summarize failed"
cat "$OUT/think/SUMMARY.txt" || true
cp "$DATA/DATA_REPORT.json" "$OUT/DATA_REPORT.json" 2>/dev/null || true
if [ "${TARBALL:-1}" = 1 ]; then
  tar czf out.tar.gz --exclude="$OUT/data" --exclude="$OUT/.installed" --exclude='*/adapter/*' --exclude='*/think_block.pt' "$OUT" || [ $? -eq 1 ]
  tar czf ckpt.tar.gz $(find "$OUT/think" \( -name adapter -o -name think_block.pt \) 2>/dev/null) 2>/dev/null || true   # weights, kept apart
  ls -la out.tar.gz ckpt.tar.gz 2>/dev/null || true
fi
echo "== think done $(date -u +%FT%TZ)"
