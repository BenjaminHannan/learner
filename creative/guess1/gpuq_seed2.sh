#!/usr/bin/env bash
# Guess-1 Stage 2 seed 2 (prereg: INCONCLUSIVE after seed 1 -> same T, --seed 2) on one 4090, K2-3.7B bf16, thinking off.
# Usage: gpuq_seed2.sh RUN_DIR_FROM_SEED1 OUT   (seed-1 rows are kept; seed-2 arms are stored as IND.s2 etc.)
set -uo pipefail
SRC=${1:?seed-1 run dir}; OUT=${2:?out}; HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"; exec > >(tee -a "$OUT/lane.log") 2>&1
[ -f "$OUT/run/target.json" ] || { mkdir -p "$OUT/run"; cp "$SRC"/{results.jsonl,target.json,menu.json,run_meta.json} "$OUT/run/"; }
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
python3 -m pip install -q --user httpx uv 2>&1 | tail -2
VV=/tmp/guess1-vllm
[ -x $VV/bin/vllm ] || { python3 -m uv venv $VV && timeout 1500 python3 -m uv pip install --python $VV/bin/python vllm 2>&1 | tail -5; }
[ -x $VV/bin/vllm ] || { echo "VLLM INSTALL FAILED"; exit 2; }
$VV/bin/vllm serve IFM/K2-Horizon-3.7B --served-model-name k2 --port 8090 --dtype bfloat16 --max-model-len 16384 \
  --gpu-memory-utilization ${GPU_UTIL:-0.85} --trust-remote-code --enable-auto-tool-choice --tool-call-parser k2_horizon \
  --chat-template "$HERE/k2_nothink.jinja" > "$OUT/vllm.log" 2>&1 &
SP=$!; trap 'kill $SP 2>/dev/null' EXIT
for i in $(seq 90); do curl -sf localhost:8090/v1/models >/dev/null && break; sleep 10; done
curl -sf localhost:8090/v1/models >/dev/null || { echo "SERVE FAILED"; grep Error "$OUT/vllm.log" | tail -8; exit 1; }
ARGS=(--base-url http://127.0.0.1:8090/v1 --model k2 --concurrency 48 --seed 2 --out "$OUT/run")
cd "$HERE"
python3 run.py arms "${ARGS[@]}" && python3 run.py topup "${ARGS[@]}"
python3 run.py report "${ARGS[@]}"; echo "$(date -u +%FT%TZ) DONE"
