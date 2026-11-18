#!/usr/bin/env bash
# Pick-1 on one GPU (4090 or Kaggle T4): serve K2-3.7B (thinking off), build pools, K2 self-judge, analyze. No new episodes.
# Usage: job.sh RESULTS_DIR OUT   (RESULTS_DIR holds results.jsonl + target.json, e.g. the Guess-1 seed-2 run dir)
# DTYPE=float16 (default; T4 has no bf16; adds --enforce-eager) or DTYPE=bfloat16 on a 4090.
set -uo pipefail
SRC=${1:?results dir}; OUT=${2:?out}; HERE=$(cd "$(dirname "$0")" && pwd); DTYPE=${DTYPE:-float16}
mkdir -p "$OUT"; exec > >(tee -a "$OUT/job.log") 2>&1
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
python3 -m pip install -q --user httpx uv 2>&1 | tail -2
export PATH="$HOME/.local/bin:$PATH"
cd "$HERE"
python3 pools.py --results "$SRC" --out "$OUT/pools.jsonl" || exit 3
VV=/tmp/guess1-vllm   # same venv path as the Guess-1 lanes, reused if present
[ -x $VV/bin/vllm ] || { python3 -m uv venv $VV && timeout 1500 python3 -m uv pip install --python $VV/bin/python vllm 2>&1 | tail -5; }
[ -x $VV/bin/vllm ] || { echo "VLLM INSTALL FAILED"; exit 2; }
EAGER=""; [ "$DTYPE" = float16 ] && EAGER="--enforce-eager"
$VV/bin/vllm serve IFM/K2-Horizon-3.7B --served-model-name k2 --port 8090 --dtype "$DTYPE" $EAGER --max-model-len 16384 \
  --gpu-memory-utilization ${GPU_UTIL:-0.85} --trust-remote-code --enable-auto-tool-choice --tool-call-parser k2_horizon \
  --chat-template "$HERE/../guess1/k2_nothink.jinja" > "$OUT/vllm.log" 2>&1 &
SP=$!; trap 'kill $SP 2>/dev/null' EXIT
for i in $(seq 90); do curl -sf localhost:8090/v1/models >/dev/null && break; sleep 10; done
curl -sf localhost:8090/v1/models >/dev/null || { echo "SERVE FAILED"; grep Error "$OUT/vllm.log" | tail -8; exit 1; }
python3 judge_k2.py --pools "$OUT/pools.jsonl" --out "$OUT/k2_scores.jsonl" --base-url http://127.0.0.1:8090/v1 --model k2 --concurrency ${CONC:-32}
# rerun once to pick up any transient failures (resumable)
python3 judge_k2.py --pools "$OUT/pools.jsonl" --out "$OUT/k2_scores.jsonl" --base-url http://127.0.0.1:8090/v1 --model k2 --concurrency ${CONC:-32}
python3 analyze.py --pools "$OUT/pools.jsonl" --k2 "$OUT/k2_scores.jsonl" --haiku "$OUT/haiku_scores.jsonl" --out "$OUT"
echo "$(date -u +%FT%TZ) DONE"
