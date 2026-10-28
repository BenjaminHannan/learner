#!/usr/bin/env bash
# Probe-3 on the Mac (PREREG.md Addendum 1): MLX, K2-Horizon-3.7B bf16 straight from IFM/K2-Horizon-3.7B (no quantization).
#   venv -> inputs check -> pools/replay gate -> build_data -> train_mlx (LoRA) -> gen_mlx tuned -> gen_mlx base (MLX-BASE) -> analyze (decision run + MLX-BASE report) -> VERDICT.md
# Usage: run_m3.sh OUT [GUESS1_RUN_DIR] [PICK1_K2_SCORES] [HAIKU_TRAIN_PROBES] [POOLS]
#   defaults are the committed copies in ../inputs (see fetch_inputs.sh). Everything lands in OUT. Safe to rerun: each stage resumes or skips.
# Env: MEM_LIMIT_GB (default 24: MLX memory + wired cap; the shared K2 q4 server keeps the rest), MAX_PRESSURE (1 = only "normal" is accepted; 2 allows "warn"),
#      PRESSURE_WAIT (seconds to wait for pressure to drop before exiting, default 300), VENV (default ~/learner-ops/probe3/.venv), PYVER (uv python, default 3.12), UPGRADE=1 (pip install -U), HAIKU_PROBES (optional
#      Haiku probes on the 48 target tasks, diagnostics only), TRAIN_ARGS / GEN_ARGS (extra flags), SMOKE=1 (tiny random model pipeline check), SAVE_EVERY (train checkpoint interval in steps, default 4), BATCH_TASKS (generation: tasks in flight, default 2).
# Exit codes: 75 = paused because macOS memory pressure was not normal (rerun the same command to resume); other non-zero = a stage failed.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); P3=$(dirname "$HERE"); P1=$(dirname "$P3")/probe1
OUT=${1:?usage: run_m3.sh OUT [GUESS1_RUN_DIR] [PICK1_K2_SCORES] [HAIKU_TRAIN_PROBES] [POOLS]}
SRC=${2:-$P3/inputs/guess1_run}; SELF=${3:-$P3/inputs/pick1/k2_scores.jsonl}; HAIKU=${4:-$P3/inputs/haiku_train_probes.jsonl}; POOLS=${5:-$P3/inputs/pick1/pools.jsonl}
VENV=${VENV:-$HOME/learner-ops/probe3/.venv}; MEM_LIMIT_GB=${MEM_LIMIT_GB:-24}; MAX_PRESSURE=${MAX_PRESSURE:-1}; PRESSURE_WAIT=${PRESSURE_WAIT:-300}
SAVE_EVERY=${SAVE_EVERY:-4}; BATCH_TASKS=${BATCH_TASKS:-2}; TRAIN_ARGS=${TRAIN_ARGS:-}; GEN_ARGS=${GEN_ARGS:-}
# SMOKE=1: random-init tiny model, a few examples and tokens (pipeline check, minutes, any machine with mlx); the numbers mean nothing.
if [ "${SMOKE:-0}" = 1 ]; then TRAIN_ARGS="--tiny --limit-train 8 --limit-val 2 --batch 2 --max-steps 2"; GEN_ARGS="--tiny --limit-tasks 2 --max-tokens 12"; fi
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
for f in "$SRC/target.json" "$SRC/results.jsonl" "$SELF" "$HAIKU" "$POOLS"; do [ -s "$f" ] || { echo "missing input: $f (see fetch_inputs.sh)"; exit 4; }; done
SRC=$(cd "$SRC" && pwd); SELF=$(cd "$(dirname "$SELF")" && pwd)/$(basename "$SELF"); HAIKU=$(cd "$(dirname "$HAIKU")" && pwd)/$(basename "$HAIKU"); POOLS=$(cd "$(dirname "$POOLS")" && pwd)/$(basename "$POOLS")
exec > >(tee -a "$OUT/run_m3.log") 2>&1
echo "== $(date -u +%FT%TZ) run_m3.sh OUT=$OUT"
export PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false HF_HUB_DISABLE_TELEMETRY=1

pressure_level() { if [ "$(uname)" = Darwin ]; then sysctl -n kern.memorystatus_vm_pressure_level 2>/dev/null || echo 1; else echo 1; fi; }
# Pause (up to PRESSURE_WAIT s) while macOS memory pressure is above MAX_PRESSURE (1 normal, 2 warn, 4 critical); then exit 75 cleanly.
check_pressure() {
  local waited=0 lv
  while :; do
    lv=$(pressure_level)
    [ "$lv" -le "$MAX_PRESSURE" ] && return 0
    if [ "$waited" -ge "$PRESSURE_WAIT" ]; then
      echo "PAUSED before '$1': macOS memory pressure level $lv (1 normal, 2 warn, 4 critical) for ${PRESSURE_WAIT}s. Free memory (is the K2 q4 server oversized?) and rerun the same command; finished stages are kept and training/generation resume."
      command -v memory_pressure >/dev/null && memory_pressure | tail -4; command -v vm_stat >/dev/null && vm_stat | head -6
      exit 75
    fi
    echo "memory pressure level $lv before '$1'; waiting 30s ($waited/${PRESSURE_WAIT}s)"; sleep 30; waited=$((waited + 30))
  done
}
# run NAME CMD...: pressure gate, run, translate exit codes (75 from the python scripts = they paused themselves after a checkpoint).
run() {
  local name=$1; shift
  check_pressure "$name"; echo "== $(date -u +%FT%TZ) $name"
  "$@"; local rc=$?
  if [ $rc -eq 75 ]; then echo "PAUSED during '$name' (memory pressure). Rerun the same command to resume."; exit 75; fi
  [ $rc -eq 0 ] || { echo "STAGE FAILED: $name (exit $rc)"; exit $rc; }
}

# --- venv with mlx-lm (latest), transformers, tokenizers
if [ "$(uname -sm)" != "Darwin arm64" ]; then echo "warning: not Apple silicon macOS ($(uname -sm)); MLX will run on CPU and be very slow"; fi
if [ ! -x "$VENV/bin/python" ]; then
  mkdir -p "$(dirname "$VENV")"
  if command -v uv >/dev/null; then uv venv --python "${PYVER:-3.12}" "$VENV" || exit 2   # mlx-lm needs Python >= 3.10 (macOS's /usr/bin/python3 is often 3.9); uv fetches one if missing
  else
    for p in python3.13 python3.12 python3.11 python3.10 python3; do command -v $p >/dev/null && $p -c 'import sys; sys.exit(sys.version_info < (3, 10))' && { $p -m venv "$VENV" && break; }; done
    [ -x "$VENV/bin/python" ] || { echo "need Python >= 3.10 (or install uv: brew install uv)"; exit 2; }
  fi
  UPGRADE=1
fi
if [ "${UPGRADE:-0}" = 1 ]; then
  if command -v uv >/dev/null; then uv pip install --python "$VENV/bin/python" -U mlx-lm transformers tokenizers huggingface_hub || exit 2
  else "$VENV/bin/python" -m pip install -q -U pip mlx-lm transformers tokenizers huggingface_hub || exit 2; fi
fi
PY=$VENV/bin/python
"$PY" -m pip list 2>/dev/null | grep -iE '^(mlx|mlx-lm|transformers|tokenizers|huggingface.hub) ' | tee "$OUT/env.txt" || "$PY" -c "import mlx_lm, transformers; print('mlx-lm', mlx_lm.__version__, 'transformers', transformers.__version__)" | tee "$OUT/env.txt"
"$PY" -c "import mlx.core as mx; print('mlx device:', mx.default_device()); print(mx.device_info())" | tee -a "$OUT/env.txt"
CAF=""; command -v caffeinate >/dev/null && CAF="caffeinate -i"   # keep the Mac awake for the multi-hour stages

"$HERE/fetch_inputs.sh" "$P3/inputs" || echo "(committed inputs not verified; using the paths given)"
[ -f "$OUT/pools.jsonl" ] || cp "$POOLS" "$OUT/pools.jsonl"
run "replay gate" bash -c "set -o pipefail; cd '$P1' && '$PY' replay.py --check --results '$SRC'"
run "build_data" bash -c "set -o pipefail; '$PY' '$P3/build_data.py' --haiku '$HAIKU' --results '$SRC' --out '$OUT/data' | tee '$OUT/build_data.txt'"
[ -s "$OUT/data/train.jsonl" ] || { echo "no training data built"; exit 6; }
[ "${SMOKE:-0}" = 1 ] || run "fetch K2 weights (HF cache, ~7.4 GB the first time)" "$PY" -c "from huggingface_hub import snapshot_download as s; print(s('IFM/K2-Horizon-3.7B', allow_patterns=['*.json','*.safetensors','*.jinja']))"

run "train_mlx (LoRA, 2 epochs)" $CAF "$PY" "$HERE/train_mlx.py" --data "$OUT/data" --out "$OUT/train" --mem-limit-gb "$MEM_LIMIT_GB" --save-every "$SAVE_EVERY" --max-pressure "$MAX_PRESSURE" $TRAIN_ARGS
[ -f "$OUT/train/adapter/adapter_config.json" ] || { echo "NO ADAPTER (see $OUT/train/train_log.jsonl)"; exit 7; }
run "gen_mlx tuned (192 samples)" $CAF "$PY" "$HERE/gen_mlx.py" --arm tuned --adapter "$OUT/train/adapter" --out-dir "$OUT" --results "$SRC" \
  --mem-limit-gb "$MEM_LIMIT_GB" --batch-tasks "$BATCH_TASKS" --max-pressure "$MAX_PRESSURE" $GEN_ARGS
run "gen_mlx base = MLX-BASE (192 samples)" $CAF "$PY" "$HERE/gen_mlx.py" --arm base --out-dir "$OUT" --results "$SRC" \
  --mem-limit-gb "$MEM_LIMIT_GB" --batch-tasks "$BATCH_TASKS" --max-pressure "$MAX_PRESSURE" $GEN_ARGS

HP=${HAIKU_PROBES:-$OUT/none_probes_haiku.jsonl}   # absent file = analyze skips the Haiku reference
run "analyze: decision run (tuned, --wrong-at 37.5)" bash -c "cd '$P1' && '$PY' analyze.py --pools '$OUT/pools.jsonl' --results '$SRC' --k2 '$SELF' --probes '$OUT/probes_k2.jsonl' --haiku-probes '$HP' --wrong-at 37.5 --out '$OUT'"
run "analyze: MLX-BASE report" bash -c "cd '$P1' && '$PY' analyze.py --pools '$OUT/pools.jsonl' --results '$SRC' --k2 '$SELF' --probes '$OUT/probes_k2base_mlx.jsonl' --haiku-probes '$HP' --wrong-at 37.5 --out '$OUT/mlx_base'"
run "verdict (Addendum 1 rule)" "$PY" "$HERE/summarize.py" "$OUT"
echo "$(date -u +%FT%TZ) DONE -> $OUT/VERDICT.md, $OUT/report.md, $OUT/mlx_base/report.md"
