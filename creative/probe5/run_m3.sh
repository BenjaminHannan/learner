#!/usr/bin/env bash
# Probe-5 on the Mac (PREREG.md): Probe-4 rerun with LFM3-1.7B on llama.cpp. One script, every stage resumable:
#   llama.cpp build check -> weights (BF16 GGUF + HF snapshot, only if missing) -> training data (Probe-3 build_data) -> LoRA training (torch + peft on MPS, vendored model code)
#   -> adapter GGUF (convert_lora_to_gguf.py) -> llama-server --jinja --lora adapter.gguf -np 4 (ONE server: adapter scale 0.0 = untuned, 1.0 = tuned, set per request)
#   -> 12 tries/task (scale 0) -> SELF (scale 0) -> TEST-B (scale 0) -> TEST-T (scale 1) -> validity gates -> analysis (probe4/analyze_e2e) -> report.md.  The server is stopped at the end (and on any exit).
# Usage: run_m3.sh [--smoke] OUT [TASKS_JSONL]
#   --smoke : 2 tasks x 2 tries, 2 training steps on 8 examples, SELF on 4 tries, tests for 2 tasks; gates are advisory, no analysis. Checks the plumbing only; the numbers mean nothing.
# Env (defaults):
#   LLAMA_CPP_DIR   llama.cpp checkout with build/bin/llama-server (default: first of ~/llama.cpp, ~/learner-ops/llama.cpp; if none, cloned+built at ~/learner-ops/llama.cpp). Built when the binary is missing
#                   or the source has no LFM3 (LFM3 support was merged to master on 2026-10-27 ~16:06Z; no tagged release). FORCE_REBUILD=1 rebuilds.
#   VENV (~/learner-ops/.venv; created and filled with torch transformers peft ... if missing)   MODELS_DIR (~/learner-ops/models)   HF_DIR ($MODELS_DIR/lfm3-1.7b-hf)   GGUF ($MODELS_DIR/gguf/LFM3-1.7B-BF16.gguf)
#   PORT (8085)  NP (4: server slots = requests in flight)  CTX (65536 total, split over the slots: 16384 each)  NGL (99)  MPS_GB (12: cap for training)  SAVE_EVERY (5 training steps)
#   FLAG_DIR (~/learner-ops): if FLAG_DIR/ASSISTANT_RUNNING exists the script waits FLAG_WAIT (300) s, then exits 75; the python stages also stop between requests (rerun the same command to resume).
#   MIN_FREE_GB (9): refuse to download when less disk is free.   AUTO_INSTALL=0 stops the script from pip-installing missing packages.
#   Low-disk order (never both 3.5 GB copies at once): STOP_AFTER_ADAPTER=1 needs only the HF weights and exits 0 once OUT/adapter.gguf exists (run it for the smoke OUT, then the real OUT);
#   then DROP_HF=1 deletes HF_DIR (only if this script downloaded it: HF_DIR/.probe5_downloaded) when OUT/adapter.gguf exists, and fetches the GGUF. Once OUT/adapter.gguf exists the HF weights are not needed.
# Exit codes: 0 done, 75 paused (assistant running / memory pressure), 8 INVALID run (a validity gate failed), 9 inputs incomplete, 2 setup problem, other = a stage failed.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); CREATIVE=$(dirname "$HERE"); P3=$CREATIVE/probe3; P4=$CREATIVE/probe4
SMOKE=0; if [ "${1:-}" = "--smoke" ]; then SMOKE=1; shift; fi
OUT=${1:?usage: run_m3.sh [--smoke] OUT [TASKS_JSONL]}
TASKS=${2:-$P4/tasks_new.jsonl}
VENV=${VENV:-$HOME/learner-ops/.venv}; MODELS_DIR=${MODELS_DIR:-$HOME/learner-ops/models}
HF_DIR=${HF_DIR:-$MODELS_DIR/lfm3-1.7b-hf}; GGUF=${GGUF:-$MODELS_DIR/gguf/LFM3-1.7B-BF16.gguf}
HF_REV=40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd; GGUF_REV=b3f2ae5d73cd3c91bf40e8ba752c648aa05dffdf     # pinned: the vendored model code is this revision's
HF_BYTES=3457635448; GGUF_BYTES=3466626336
PORT=${PORT:-8085}; NP=${NP:-4}; CTX=${CTX:-65536}; NGL=${NGL:-99}; MPS_GB=${MPS_GB:-12}; SAVE_EVERY=${SAVE_EVERY:-5}
FLAG_DIR=${FLAG_DIR:-$HOME/learner-ops}; FLAG_WAIT=${FLAG_WAIT:-300}; MIN_FREE_GB=${MIN_FREE_GB:-9}; MAX_PRESSURE=${MAX_PRESSURE:-1}; PRESSURE_WAIT=${PRESSURE_WAIT:-300}
TRIES=${TRIES:-12}; URL=http://127.0.0.1:$PORT
TRAIN_ARGS=""; SELF_ARGS=""; GEN_ARGS=""; GATE_ARGS=""; CHECK_ARGS=""
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd); TASKS=$(cd "$(dirname "$TASKS")" && pwd)/$(basename "$TASKS")
[ -s "$TASKS" ] || { echo "missing task file: $TASKS"; exit 2; }
if [ "$SMOKE" = 1 ]; then
  TRIES=2; head -2 "$TASKS" > "$OUT/tasks_smoke.jsonl"; TASKS=$OUT/tasks_smoke.jsonl
  TRAIN_ARGS="--limit-train 8 --limit-val 4 --batch 2 --max-steps 2"; SELF_ARGS="--limit 4"; GATE_ARGS="--advisory --tries 2"; CHECK_ARGS="--min-diff 1e-6"      # 2 training steps barely move the weights
fi
sha() { if command -v shasum >/dev/null; then shasum -a 256 "$1" | cut -d' ' -f1; else sha256sum "$1" | cut -d' ' -f1; fi; }
exec > >(tee -a "$OUT/run_m3.log") 2>&1
echo "== $(date -u +%FT%TZ) probe5 run_m3.sh OUT=$OUT smoke=$SMOKE tasks=$TASKS ($(wc -l < "$TASKS" | tr -d ' ') tasks, sha256 $(sha "$TASKS"))"
export PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false HF_HUB_DISABLE_TELEMETRY=1 PYTORCH_ENABLE_MPS_FALLBACK=1 ASSISTANT_FLAG=$FLAG_DIR/ASSISTANT_RUNNING
T_START=$(date +%s); SERVER_PID=""; SAMPLER_PID=""; STAGES="$OUT/stage_times.tsv"; : > "$STAGES"

# ---------- helpers ----------
stop_server() {
  [ -n "$SAMPLER_PID" ] && kill "$SAMPLER_PID" 2>/dev/null
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "== stopping llama-server (pid $SERVER_PID)"; kill "$SERVER_PID" 2>/dev/null
    for _ in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$SERVER_PID" 2>/dev/null || break; sleep 1; done
    kill -9 "$SERVER_PID" 2>/dev/null
  fi
  SERVER_PID=""; SAMPLER_PID=""
}
trap 'stop_server' EXIT
trap 'echo "interrupted"; exit 130' INT TERM

wait_flag() {     # wait while ASSISTANT_RUNNING exists, then exit 75
  local waited=0
  while [ -e "$FLAG_DIR/ASSISTANT_RUNNING" ]; do
    if [ "$waited" -ge "$FLAG_WAIT" ]; then
      echo "PAUSED before '$1': $FLAG_DIR/ASSISTANT_RUNNING exists (the assistant is using the Mac). Rerun the same command later; finished stages are kept."; exit 75
    fi
    echo "ASSISTANT_RUNNING exists before '$1'; waiting 30s ($waited/${FLAG_WAIT}s)"; sleep 30; waited=$((waited + 30))
  done
}
pressure_level() { if [ "$(uname)" = Darwin ]; then sysctl -n kern.memorystatus_vm_pressure_level 2>/dev/null || echo 1; else echo 1; fi; }
check_pressure() {
  local waited=0 lv
  while :; do
    lv=$(pressure_level); [ "$lv" -le "$MAX_PRESSURE" ] && return 0
    if [ "$waited" -ge "$PRESSURE_WAIT" ]; then echo "PAUSED before '$1': macOS memory pressure level $lv for ${PRESSURE_WAIT}s. Free memory and rerun the same command."; exit 75; fi
    echo "memory pressure level $lv before '$1'; waiting 30s"; sleep 30; waited=$((waited + 30))
  done
}
run() {           # run NAME CMD...: pause checks, time it, translate exit codes
  local name=$1; shift
  wait_flag "$name"; check_pressure "$name"; echo "== $(date -u +%FT%TZ) $name"
  local t0 rc; t0=$(date +%s); "$@"; rc=$?
  printf '%s\t%s\n' "$name" "$(( $(date +%s) - t0 ))" >> "$STAGES"
  if [ $rc -eq 75 ]; then echo "PAUSED during '$name'. Rerun the same command to resume."; exit 75; fi
  [ $rc -eq 0 ] || { echo "STAGE FAILED: $name (exit $rc)"; exit $rc; }
}
free_gb() { df -k "$1" 2>/dev/null | awk 'NR==2{print int($4/1048576)}'; }
filesize() { if [ "$(uname)" = Darwin ]; then stat -f %z "$1" 2>/dev/null || echo 0; else stat -c %s "$1" 2>/dev/null || echo 0; fi; }

# ---------- venv ----------
need_py='import torch, transformers, peft, safetensors, numpy, huggingface_hub, gguf, sentencepiece'
if [ ! -x "$VENV/bin/python" ]; then
  mkdir -p "$(dirname "$VENV")"
  if command -v uv >/dev/null; then uv venv --python "${PYVER:-3.12}" "$VENV" || exit 2
  else
    for p in python3.13 python3.12 python3.11 python3.10 python3; do command -v $p >/dev/null && $p -c 'import sys; sys.exit(sys.version_info < (3, 10))' && { $p -m venv "$VENV" && break; }; done
    [ -x "$VENV/bin/python" ] || { echo "need Python >= 3.10 (or install uv)"; exit 2; }
  fi
fi
PY=$VENV/bin/python
if ! "$PY" -c "$need_py" 2>/dev/null; then
  [ "${AUTO_INSTALL:-1}" = 1 ] || { echo "venv $VENV lacks packages ($need_py); install them or unset AUTO_INSTALL=0"; exit 2; }
  PKGS="torch transformers>=5.12 peft safetensors numpy huggingface_hub gguf sentencepiece psutil pytest"
  if command -v uv >/dev/null; then uv pip install --python "$PY" $PKGS || exit 2; else "$PY" -m pip install -q -U pip && "$PY" -m pip install -q $PKGS || exit 2; fi
fi
"$PY" -c "
import torch, transformers, peft, sys
print('python', sys.version.split()[0], 'torch', torch.__version__, 'transformers', transformers.__version__, 'peft', peft.__version__, 'mps', getattr(torch.backends, 'mps', None) and torch.backends.mps.is_available())" | tee "$OUT/env.txt"
"$PY" -c "import sys; sys.path.insert(0,'$HERE'); import lfm3_load as L; b=L.check_hashes(); print('vendored model files differ:', b) if b else print('vendored LFM3 code intact (revision', L.PINNED_REVISION + ')')" | tee -a "$OUT/env.txt"
CAF=""; command -v caffeinate >/dev/null && CAF="caffeinate -i"

# ---------- llama.cpp ----------
if [ -z "${LLAMA_CPP_DIR:-}" ]; then
  for d in "$HOME/llama.cpp" "$HOME/learner-ops/llama.cpp"; do [ -d "$d" ] && { LLAMA_CPP_DIR=$d; break; }; done
  LLAMA_CPP_DIR=${LLAMA_CPP_DIR:-$HOME/learner-ops/llama.cpp}
fi
SERVER_BIN=$LLAMA_CPP_DIR/build/bin/llama-server
has_lfm3() { grep -q "LLM_ARCH_LFM3" "$LLAMA_CPP_DIR/src/llama-arch.cpp" 2>/dev/null && grep -rqi "lfm3" "$LLAMA_CPP_DIR/convert_hf_to_gguf.py" "$LLAMA_CPP_DIR/conversion" 2>/dev/null; }
if [ ! -d "$LLAMA_CPP_DIR/.git" ] && [ ! -d "$LLAMA_CPP_DIR/src" ]; then
  wait_flag "clone llama.cpp"; echo "== cloning llama.cpp -> $LLAMA_CPP_DIR"; mkdir -p "$(dirname "$LLAMA_CPP_DIR")"
  git clone --depth 1 https://github.com/ggml-org/llama.cpp "$LLAMA_CPP_DIR" || exit 2
fi
if ! has_lfm3 && [ -d "$LLAMA_CPP_DIR/.git" ]; then
  echo "== $LLAMA_CPP_DIR has no LFM3 support yet; updating"; if ! git -C "$LLAMA_CPP_DIR" pull --ff-only; then git -C "$LLAMA_CPP_DIR" fetch --depth 1 origin master && git -C "$LLAMA_CPP_DIR" reset --hard FETCH_HEAD; fi
  rm -f "$SERVER_BIN"
fi
has_lfm3 || { echo "llama.cpp at $LLAMA_CPP_DIR still has no LFM3 (need a master from after 2026-10-27 16:06Z)"; exit 2; }
if [ ! -x "$SERVER_BIN" ] || [ "${FORCE_REBUILD:-0}" = 1 ]; then
  wait_flag "build llama.cpp"; echo "== building llama-server in $LLAMA_CPP_DIR (Metal is on by default on macOS)"
  ( cd "$LLAMA_CPP_DIR" && cmake -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF && cmake --build build -j --target llama-server ) || { echo "llama.cpp build failed"; exit 2; }
fi
[ -f "$LLAMA_CPP_DIR/convert_lora_to_gguf.py" ] || { echo "no convert_lora_to_gguf.py in $LLAMA_CPP_DIR"; exit 2; }
echo "llama.cpp: $(git -C "$LLAMA_CPP_DIR" log -1 --format='%H %cI' 2>/dev/null || echo 'not a git checkout') ($SERVER_BIN)" | tee -a "$OUT/env.txt"

# ---------- weights (only if missing) ----------
[ ! -f "$HF_DIR/model.safetensors" ] || [ "$(filesize "$HF_DIR/model.safetensors")" = "$HF_BYTES" ] || echo "note: $HF_DIR/model.safetensors has $(filesize "$HF_DIR/model.safetensors") bytes, the pinned revision has $HF_BYTES (a partial download? delete it to re-fetch)"
[ ! -f "$GGUF" ] || [ "$(filesize "$GGUF")" = "$GGUF_BYTES" ] || echo "note: $GGUF has $(filesize "$GGUF") bytes, the pinned revision has $GGUF_BYTES"
have_adapter=0; [ -s "$OUT/adapter.gguf" ] && have_adapter=1
need_hf=0; [ $have_adapter = 1 ] || [ -f "$HF_DIR/model.safetensors" ] && [ -f "$HF_DIR/config.json" ] && [ -f "$HF_DIR/tokenizer.json" ] || need_hf=1
need_gguf=0; [ -f "$GGUF" ] || [ "${STOP_AFTER_ADAPTER:-0}" = 1 ] || need_gguf=1
if [ "${DROP_HF:-0}" = 1 ] && [ $have_adapter = 1 ] && [ -f "$HF_DIR/.probe5_downloaded" ]; then
  echo "== DROP_HF=1: OUT/adapter.gguf exists; deleting the HF weights this script downloaded ($HF_DIR) before the GGUF download"; rm -rf "$HF_DIR"
fi
if [ $need_hf = 1 ] || [ $need_gguf = 1 ]; then
  fg=$(free_gb "$(dirname "$MODELS_DIR")"); [ -d "$MODELS_DIR" ] && fg=$(free_gb "$MODELS_DIR")
  [ "${fg:-0}" -ge "$MIN_FREE_GB" ] || { echo "only ${fg:-?} GB free where the models go; need $MIN_FREE_GB GB (set MIN_FREE_GB or free disk)"; exit 2; }
  mkdir -p "$MODELS_DIR"
fi
if [ $need_hf = 1 ]; then
  wait_flag "download HF weights"; echo "== downloading LiquidAI/LFM3-1.7B @ $HF_REV (weights + tokenizer, no code files) -> $HF_DIR"
  "$PY" -c "
from huggingface_hub import snapshot_download as s
print(s('LiquidAI/LFM3-1.7B', revision='$HF_REV', local_dir='$HF_DIR', allow_patterns=['*.safetensors','config.json','generation_config.json','tokenizer*','special_tokens_map.json','chat_template.jinja']))" || { echo "HF download failed (rerun to resume)"; exit 2; }
  touch "$HF_DIR/.probe5_downloaded"
fi
if [ $need_gguf = 1 ]; then
  wait_flag "download BF16 GGUF"; echo "== downloading LiquidAI/LFM3-1.7B-GGUF @ $GGUF_REV LFM3-1.7B-BF16.gguf -> $GGUF"
  mkdir -p "$(dirname "$GGUF")"
  "$PY" -c "
from huggingface_hub import hf_hub_download as d
import os, shutil
p = d('LiquidAI/LFM3-1.7B-GGUF', 'LFM3-1.7B-BF16.gguf', revision='$GGUF_REV', local_dir=os.path.dirname('$GGUF'))
if os.path.abspath(p) != os.path.abspath('$GGUF'): shutil.move(p, '$GGUF')
print(p)" || { echo "GGUF download failed (rerun to resume)"; exit 2; }
fi
{ [ -f "$GGUF" ] || [ "${STOP_AFTER_ADAPTER:-0}" = 1 ]; } && { [ -f "$HF_DIR/model.safetensors" ] || [ $have_adapter = 1 ]; } || { echo "weights missing after download"; exit 2; }
echo "weights: $HF_DIR ($(filesize "$HF_DIR/model.safetensors") bytes safetensors), $GGUF ($(filesize "$GGUF") bytes); disk free $(free_gb "$OUT") GB" | tee -a "$OUT/env.txt"

# ---------- training data + LoRA ----------
run "replay gate on the Probe-3 source runs" bash -c "set -o pipefail; cd '$CREATIVE/probe1' && '$PY' replay.py --check --results '$P3/inputs/guess1_run'"
run "build_data (Probe-3 449/49 sets)" bash -c "set -o pipefail; '$PY' '$P3/build_data.py' --haiku '$P3/inputs/haiku_train_probes.jsonl' --results '$P3/inputs/guess1_run' --out '$OUT/data' | tee '$OUT/build_data.txt'"
[ -s "$OUT/data/train.jsonl" ] || { echo "no training data built"; exit 6; }
if [ "$SMOKE" != 1 ]; then
  [ "$(wc -l < "$OUT/data/train.jsonl" | tr -d ' ')" = 449 ] && [ "$(wc -l < "$OUT/data/val.jsonl" | tr -d ' ')" = 49 ] || { echo "training data is not 449 train / 49 val sets (the Probe-3 data)"; exit 6; }
fi
run "train_lora_lfm3 (torch + peft, MPS)" $CAF "$PY" "$HERE/train_lora_lfm3.py" --model "$HF_DIR" --data "$OUT/data" --out "$OUT/train" --mps-gb "$MPS_GB" --save-every "$SAVE_EVERY" $TRAIN_ARGS
[ -f "$OUT/train/adapter/adapter_model.safetensors" ] || { echo "NO ADAPTER (see $OUT/train/train_log.jsonl)"; exit 7; }
if [ ! -s "$OUT/adapter.gguf" ]; then
  run "convert_lora_to_gguf" "$PY" "$LLAMA_CPP_DIR/convert_lora_to_gguf.py" "$OUT/train/adapter" --base "$HF_DIR" --outfile "$OUT/adapter.gguf.tmp" --outtype f32
  mv "$OUT/adapter.gguf.tmp" "$OUT/adapter.gguf"
fi
echo "adapter.gguf: $(filesize "$OUT/adapter.gguf") bytes"
if [ "${STOP_AFTER_ADAPTER:-0}" = 1 ]; then echo "$(date -u +%FT%TZ) STOP_AFTER_ADAPTER: adapter ready; rerun without it (DROP_HF=1 to free the HF weights first) for the server stages"; exit 0; fi

# ---------- server ----------
wait_flag "start llama-server"; check_pressure "start llama-server"
if curl -sf "$URL/health" >/dev/null 2>&1; then echo "something already answers at $URL; set PORT to a free port"; exit 2; fi
echo "== $(date -u +%FT%TZ) starting llama-server: -m $GGUF --lora $OUT/adapter.gguf -np $NP -c $CTX --jinja (port $PORT)"
"$SERVER_BIN" -m "$GGUF" --lora "$OUT/adapter.gguf" -np "$NP" -c "$CTX" -ngl "$NGL" --jinja --host 127.0.0.1 --port "$PORT" > "$OUT/server.log" 2>&1 &
SERVER_PID=$!
( peak=0; while kill -0 "$SERVER_PID" 2>/dev/null; do r=$(ps -o rss= -p "$SERVER_PID" 2>/dev/null | tr -d ' '); [ -n "$r" ] && [ "$r" -gt "$peak" ] && { peak=$r; echo "$peak" > "$OUT/server_rss_peak_kb.txt"; }; sleep 5; done ) &
SAMPLER_PID=$!
for i in $(seq 1 120); do
  curl -sf "$URL/health" >/dev/null 2>&1 && break
  kill -0 "$SERVER_PID" 2>/dev/null || { echo "llama-server exited early; see $OUT/server.log"; tail -20 "$OUT/server.log"; exit 3; }
  sleep 2
done
curl -sf "$URL/health" >/dev/null 2>&1 || { echo "llama-server did not become healthy in 240 s"; tail -20 "$OUT/server.log"; exit 3; }
curl -sf "$URL/props" > "$OUT/server_props.json" 2>/dev/null || true      # server defaults (top_k, min_p, repeat penalty ... that the prereg does not set) are recorded here
run "check: adapter scale changes the logits, logprobs present" "$PY" "$HERE/llm_server.py" --url "$URL" --check $CHECK_ARGS

# ---------- pipeline ----------
run "tries: 12 per task, adapter scale 0 (agent_lfm3)" $CAF "$PY" "$HERE/agent_lfm3.py" --tasks "$TASKS" --out "$OUT/tries" --tries "$TRIES" --url "$URL" --parallel "$NP"
run "SELF judge (self_lfm3)" $CAF "$PY" "$HERE/self_lfm3.py" --tries "$OUT/tries/results.jsonl" --tasks "$TASKS" --pools "$OUT/pools.jsonl" --out "$OUT/self_scores.jsonl" --url "$URL" --parallel "$NP" $SELF_ARGS
run "TEST-B: untuned LFM3 writes tests (scale 0)" $CAF "$PY" "$HERE/gen_tests_lfm3.py" --arm base --tasks-file "$TASKS" --out-dir "$OUT/tests_b" --url "$URL" --parallel "$NP" $GEN_ARGS
run "TEST-T: LFM3 + LoRA writes tests (scale 1)" $CAF "$PY" "$HERE/gen_tests_lfm3.py" --arm tuned --tasks-file "$TASKS" --out-dir "$OUT/tests_t" --url "$URL" --parallel "$NP" $GEN_ARGS
stop_server       # nothing below needs the model

# ---------- gates, then analysis ----------
echo "== $(date -u +%FT%TZ) validity gates"
"$PY" "$HERE/check_gates.py" --out "$OUT" --tasks "$TASKS" $GATE_ARGS; GRC=$?
if [ $GRC -ne 0 ]; then echo "RUN INVALID (gate exit $GRC): no picker result is read. See $OUT/gates.json; fix the fault and repeat the run once."; fi
python_stats() { "$PY" - "$OUT" "$T_START" <<'EOF'
import json, os, sys, time
out, t0 = sys.argv[1], int(sys.argv[2])
st = {}
for l in open(os.path.join(out, "stage_times.tsv")):
    if l.strip():
        n, s = l.rstrip("\n").rsplit("\t", 1)
        st[n] = int(s)
d = dict(stage_seconds=st, wall_seconds=int(time.time()) - t0)
p = os.path.join(out, "server_rss_peak_kb.txt")
if os.path.exists(p):
    d["server_rss_peak_gb"] = round(int(open(p).read()) / 2**20, 2)     # RSS only: Metal buffers may not be counted; see Activity Monitor for the footprint
p = os.path.join(out, "train", "train_summary.json")
if os.path.exists(p):
    s = json.load(open(p))
    d["train"] = {k: s.get(k) for k in ("train_wall_s", "peak_driver_gb", "peak_rss_gb", "val_loss_before", "val_loss_after", "device", "dtype")}
json.dump(d, open(os.path.join(out, "run_stats.json"), "w"), indent=1)
print(json.dumps(d))
EOF
}
if [ "$SMOKE" = 1 ]; then
  python_stats; echo "SMOKE: skipping the analysis (needs 12 tries per task)"; echo "$(date -u +%FT%TZ) SMOKE DONE"; exit 0
fi
[ $GRC -eq 0 ] || { python_stats; exit $GRC; }
run "analyze_p5 (probe4 analyze_e2e on the LFM3 outputs)" "$PY" "$HERE/analyze_p5.py" --tasks "$TASKS" --tries "$OUT/tries/results.jsonl" --self "$OUT/self_scores.jsonl" \
  --test-b "$OUT/tests_b/probes_lfm3base.jsonl" --test-t "$OUT/tests_t/probes_lfm3.jsonl" --out "$OUT"
python_stats
echo "$(date -u +%FT%TZ) DONE -> $OUT/report.md, $OUT/gates.json, $OUT/run_stats.json (wall $(( $(date +%s) - T_START )) s)"
