#!/bin/bash
# Reach-1 on a Kaggle 2x T4 box: build llama.cpp (CUDA, sm_75), fetch a Qwen3.6-35B-A3B Q4_K_M GGUF, serve it split
# across both GPUs, run Reach-1 with thinking off. Usage: bash kaggle_lane.sh OUT [speed|full|half]
#   speed: 10 tasks x 8 screen tries only, prints episodes/min and the projected full-run hours, then exits.
#   full / half: the preregistered run (half = addendum-1 subset), stops launching episodes after 9.5 h.
set -uo pipefail
OUT=${1:?out dir}; MODE=${2:-speed}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"; exec > >(tee -a "$OUT/lane.log") 2>&1
echo "$(date -u +%FT%TZ) mode=$MODE"; nvidia-smi --query-gpu=name,memory.total --format=csv

# 1. llama.cpp with CUDA for T4 (sm_75)
LC=/kaggle/working/llama.cpp
if [ ! -x "$LC/build/bin/llama-server" ]; then
  git clone --depth 1 https://github.com/ggml-org/llama.cpp "$LC" && \
  cmake -S "$LC" -B "$LC/build" -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release && \
  cmake --build "$LC/build" --target llama-server -j "$(nproc)" || { echo "BUILD FAILED"; echo "build failed" > "$OUT/backend.txt"; exit 1; }
fi
(cd "$LC" && echo "llama.cpp $(git rev-parse --short HEAD) CUDA sm_75" > "$OUT/backend.txt")

# 2. GGUF: first Q4_K_M of Qwen3.6-35B-A3B found on the Hub (preferred publishers first)
pip install -q huggingface_hub httpx >/dev/null
GGUF=$(python3 - "$OUT" <<'EOF'
import sys, re
from huggingface_hub import HfApi, hf_hub_download
api, pref = HfApi(), ["Qwen", "unsloth", "bartowski", "lmstudio-community", "ggml-org"]
repos = [m.id for m in api.list_models(search="Qwen3.6-35B-A3B", limit=200) if "gguf" in m.id.lower()]
repos.sort(key=lambda r: (pref.index(r.split("/")[0]) if r.split("/")[0] in pref else 99, r))
for r in repos:
    files = sorted(f for f in api.list_repo_files(r) if f.endswith(".gguf") and re.search(r"q4_k_m", f, re.I))
    if not files:
        continue
    paths = [hf_hub_download(r, f, local_dir="/kaggle/working/gguf") for f in files]
    open(sys.argv[1] + "/backend.txt", "a").write(f"gguf {r} {files}\n")
    print(paths[0]); break
EOF
)
[ -f "$GGUF" ] || { echo "NO GGUF FOUND"; exit 1; }

# 3. one server over both T4s; 8 slots x 8k context; thinking turned off per request
"$LC/build/bin/llama-server" -m "$GGUF" --port 8080 -ngl 99 --split-mode layer -c 65536 -np 8 --jinja \
  --host 127.0.0.1 > "$OUT/server.log" 2>&1 &
SP=$!; trap 'kill $SP 2>/dev/null' EXIT
for i in $(seq 120); do curl -sf localhost:8080/health >/dev/null && break; sleep 10; done
curl -sf localhost:8080/health >/dev/null || { echo "SERVER DID NOT START"; tail -50 "$OUT/server.log"; exit 1; }

ARGS=(--base-url http://127.0.0.1:8080/v1 --model qwen3.6 --concurrency 8
      --extra-body '{"chat_template_kwargs":{"enable_thinking":false}}')
cd "$HERE"
if [ "$MODE" = speed ]; then
  T0=$(date +%s)
  python3 run.py screen "${ARGS[@]}" --out "$OUT/speed" --limit 10
  N=$(wc -l < "$OUT/speed/results.jsonl"); S=$(( $(date +%s) - T0 ))
  python3 - "$N" "$S" "$OUT/speed/results.jsonl" <<'EOF'
import sys, json
n, s = int(sys.argv[1]), int(sys.argv[2]); rows = [json.loads(l) for l in open(sys.argv[3])]
rate = n / max(s, 1) * 60
# full run estimate: 3360 screen + 56 extra tries on tasks with 0/8 (fraction from this sample) + ~48 per hard task
fail = sum(1 for t in {r["task_id"] for r in rows} if not any(r["success"] for r in rows if r["task_id"] == t)) / 10
eps = 3360 + 420 * fail * (56 + 48)
print(f"SPEED {n} episodes in {s}s = {rate:.1f}/min; tool calls in {sum(any(m.get('tool_calls') for m in r['transcript']) for r in rows)}/{n}; "
      f"successes {sum(r['success'] for r in rows)}; 0/8 tasks {fail:.0%}; projected full run {eps/rate/60:.1f} h, half {eps/2/rate/60:.1f} h")
EOF
else
  [ "$MODE" = half ] && ARGS+=(--half)
  python3 run.py all "${ARGS[@]}" --out "$OUT/run" --deadline-hours 9.5
fi
echo "$(date -u +%FT%TZ) done"
