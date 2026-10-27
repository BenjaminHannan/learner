#!/usr/bin/env bash
# Probe-4 on the Mac (PREREG.md): K2-Horizon-3.7B bf16 on MLX. Stages, each resumable:
#   12 tries per task (agent_mlx) -> SELF judge (self_mlx) -> TEST-B (gen_mlx base) -> TEST-T (gen_mlx + Probe-3 adapter) -> analyze_e2e -> report.md
# Usage: run_m3.sh OUT [TASKS_JSONL] [ADAPTER_DIR]
#   defaults: TASKS_JSONL = probe4/tasks_new.jsonl (committed before this runs), ADAPTER_DIR = ~/probe3-out/train/adapter (what Probe-3's run_m3.sh left: OUT/train/adapter).
# Env: MEM_LIMIT_GB (24), MAX_PRESSURE (1), PRESSURE_WAIT (300 s), VENV (default: Probe-3's ~/learner-ops/probe3/.venv), BATCH (episodes in flight, 12), BATCH_TASKS (test-writing tasks in flight, 3),
#      TRIES (12), SMOKE=1 (tiny random model, 2 tasks x 2 tries: pipeline check only).
# Exit 75 = paused for macOS memory pressure (rerun the same command); other non-zero = a stage failed.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); P3M=$(dirname "$HERE")/probe3/mlx; P1=$(dirname "$HERE")/probe1
OUT=${1:?usage: run_m3.sh OUT [TASKS_JSONL] [ADAPTER_DIR]}
TASKS=${2:-$HERE/tasks_new.jsonl}; ADAPTER=${3:-$HOME/probe3-out/train/adapter}
VENV=${VENV:-$HOME/learner-ops/probe3/.venv}; MEM_LIMIT_GB=${MEM_LIMIT_GB:-24}; MAX_PRESSURE=${MAX_PRESSURE:-1}; PRESSURE_WAIT=${PRESSURE_WAIT:-300}
BATCH=${BATCH:-12}; BATCH_TASKS=${BATCH_TASKS:-3}; TRIES=${TRIES:-12}
AGENT_ARGS=""; SELF_ARGS=""; GEN_ARGS=""
if [ "${SMOKE:-0}" = 1 ]; then TRIES=2; AGENT_ARGS="--tiny --limit-tasks 2 --max-tokens 16"; SELF_ARGS="--tiny --limit 3"; GEN_ARGS="--tiny --limit-tasks 1 --max-tokens 12"; fi
[ -s "$TASKS" ] || { echo "missing task file: $TASKS (run gen_tasks.py, validate_tasks.py first)"; exit 4; }
if [ "${SMOKE:-0}" != 1 ]; then [ -f "$ADAPTER/adapter_config.json" ] || { echo "no Probe-3 adapter at $ADAPTER (expected adapter_config.json + adapters.safetensors)"; exit 4; }; fi
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd); TASKS=$(cd "$(dirname "$TASKS")" && pwd)/$(basename "$TASKS")
exec > >(tee -a "$OUT/run_m3.log") 2>&1
echo "== $(date -u +%FT%TZ) probe4 run_m3.sh OUT=$OUT tasks=$TASKS ($(wc -l < "$TASKS") tasks, sha256 $(shasum -a 256 "$TASKS" | cut -d' ' -f1))"
export PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false HF_HUB_DISABLE_TELEMETRY=1

pressure_level() { if [ "$(uname)" = Darwin ]; then sysctl -n kern.memorystatus_vm_pressure_level 2>/dev/null || echo 1; else echo 1; fi; }
check_pressure() {
  local waited=0 lv
  while :; do
    lv=$(pressure_level)
    [ "$lv" -le "$MAX_PRESSURE" ] && return 0
    if [ "$waited" -ge "$PRESSURE_WAIT" ]; then
      echo "PAUSED before '$1': macOS memory pressure level $lv (1 normal, 2 warn, 4 critical) for ${PRESSURE_WAIT}s. Free memory and rerun the same command; finished stages are kept."
      exit 75
    fi
    echo "memory pressure level $lv before '$1'; waiting 30s ($waited/${PRESSURE_WAIT}s)"; sleep 30; waited=$((waited + 30))
  done
}
run() {
  local name=$1; shift
  check_pressure "$name"; echo "== $(date -u +%FT%TZ) $name"
  "$@"; local rc=$?
  if [ $rc -eq 75 ]; then echo "PAUSED during '$name' (memory pressure). Rerun the same command to resume."; exit 75; fi
  [ $rc -eq 0 ] || { echo "STAGE FAILED: $name (exit $rc)"; exit $rc; }
}

[ -x "$VENV/bin/python" ] || { echo "no venv at $VENV: run probe3/mlx/run_m3.sh once (it builds it) or set VENV"; exit 2; }
PY=$VENV/bin/python
"$PY" -c "import mlx.core as mx, mlx_lm, transformers; print('mlx-lm', mlx_lm.__version__, 'transformers', transformers.__version__, mx.default_device()); print(mx.device_info())" | tee "$OUT/env.txt" || exit 2
CAF=""; command -v caffeinate >/dev/null && CAF="caffeinate -i"

run "tries: 12 per task (agent_mlx)" $CAF "$PY" "$HERE/agent_mlx.py" --tasks "$TASKS" --out "$OUT/tries" --tries "$TRIES" --batch "$BATCH" --mem-limit-gb "$MEM_LIMIT_GB" --max-pressure "$MAX_PRESSURE" $AGENT_ARGS
run "SELF judge (self_mlx)" $CAF "$PY" "$HERE/self_mlx.py" --tries "$OUT/tries/results.jsonl" --tasks "$TASKS" --pools "$OUT/pools.jsonl" --out "$OUT/self_scores.jsonl" --mem-limit-gb "$MEM_LIMIT_GB" --max-pressure "$MAX_PRESSURE" $SELF_ARGS
run "TEST-B: untuned K2 writes tests (gen_mlx base)" $CAF "$PY" "$P3M/gen_mlx.py" --arm base --tasks-file "$TASKS" --out-dir "$OUT/tests_b" --mem-limit-gb "$MEM_LIMIT_GB" --batch-tasks "$BATCH_TASKS" --max-pressure "$MAX_PRESSURE" $GEN_ARGS
if [ "${SMOKE:-0}" = 1 ]; then echo "SMOKE: skipping TEST-T and the analysis (needs a real adapter and 12 tries)"; echo "$(date -u +%FT%TZ) SMOKE DONE"; exit 0; fi
run "TEST-T: K2 + Probe-3 LoRA writes tests (gen_mlx tuned)" $CAF "$PY" "$P3M/gen_mlx.py" --arm tuned --adapter "$ADAPTER" --tasks-file "$TASKS" --out-dir "$OUT/tests_t" --mem-limit-gb "$MEM_LIMIT_GB" --batch-tasks "$BATCH_TASKS" --max-pressure "$MAX_PRESSURE"
run "analyze_e2e" "$PY" "$HERE/analyze_e2e.py" --tasks "$TASKS" --tries "$OUT/tries/results.jsonl" --self "$OUT/self_scores.jsonl" --test-b "$OUT/tests_b/probes_k2base_mlx.jsonl" --test-t "$OUT/tests_t/probes_k2.jsonl" --out "$OUT"
echo "$(date -u +%FT%TZ) DONE -> $OUT/report.md"
