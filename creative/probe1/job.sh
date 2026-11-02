#!/usr/bin/env bash
# Probe-1 on one Kaggle T4 (PREREG.md): CPU replay gate, serve K2-3.7B (fp16, thinking off), K2 writes 4 probe samples per task, analyze.
# Haiku reference probes are separate (Batches API, no GPU): write_probes.py --haiku; analyze picks up probes_haiku.jsonl from OUT if present.
# Usage: job.sh RESULTS_DIR PICK1_K2_SCORES OUT
#   RESULTS_DIR: Guess-1 seed-2 run dir (results.jsonl + target.json); PICK1_K2_SCORES: Pick-1 k2_scores.jsonl (SELF, required).
# DTYPE=float16 (default; adds --enforce-eager) or DTYPE=bfloat16 on a 4090.
set -uo pipefail
SRC=${1:?results dir}; SELF=${2:?Pick-1 k2_scores.jsonl}; OUT=${3:?out}; HERE=$(cd "$(dirname "$0")" && pwd); DTYPE=${DTYPE:-float16}
[ -s "$SELF" ] || { echo "missing Pick-1 SELF scores: $SELF"; exit 4; }
mkdir -p "$OUT"; SELF=$(readlink -f "$SELF"); SRC=$(readlink -f "$SRC"); exec > >(tee -a "$OUT/job.log") 2>&1
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
python3 -m pip install -q --user httpx uv 2>&1 | tail -2
export PATH="$HOME/.local/bin:$PATH"
cd "$HERE"
python3 ../pick1/pools.py --results "$SRC" --out "$OUT/pools.jsonl" || exit 3
python3 replay.py --check --results "$SRC" || { echo "REPLAY GATE FAILED"; exit 5; }
pkill -f "[v]llm serve" 2>/dev/null; sleep 2
VV=/tmp/guess1-vllm   # same venv path as the Guess-1 / Pick lanes, reused if present
[ -x $VV/bin/vllm ] || { python3 -m uv venv $VV && timeout 1500 python3 -m uv pip install --python $VV/bin/python vllm 2>&1 | tail -5; }
[ -x $VV/bin/vllm ] || { echo "VLLM INSTALL FAILED"; exit 2; }
EAGER=""; [ "$DTYPE" = float16 ] && EAGER="--enforce-eager"
$VV/bin/vllm serve IFM/K2-Horizon-3.7B --served-model-name k2 --port 8090 --dtype "$DTYPE" $EAGER --max-model-len 16384 \
  --gpu-memory-utilization ${GPU_UTIL:-0.85} --trust-remote-code --enable-auto-tool-choice --tool-call-parser k2_horizon \
  --chat-template "$HERE/../guess1/k2_nothink.jinja" > "$OUT/vllm.log" 2>&1 &
SP=$!; trap 'kill $SP 2>/dev/null; pkill -f "[v]llm serve" 2>/dev/null' EXIT
for i in $(seq 90); do curl -sf localhost:8090/v1/models >/dev/null && break; sleep 10; done
curl -sf localhost:8090/v1/models >/dev/null || { echo "SERVE FAILED"; grep Error "$OUT/vllm.log" | tail -8; exit 1; }
for pass in 1 2; do   # second pass resumes after transient failures
  python3 write_probes.py --results "$SRC" --base-url http://127.0.0.1:8090/v1 --model k2 --concurrency ${CONC:-16} --out "$OUT/probes_k2.jsonl"
done
kill $SP 2>/dev/null; pkill -f "[v]llm serve" 2>/dev/null
python3 analyze.py --pools "$OUT/pools.jsonl" --results "$SRC" --k2 "$SELF" --probes "$OUT/probes_k2.jsonl" --haiku-probes "$OUT/probes_haiku.jsonl" --out "$OUT"
echo "$(date -u +%FT%TZ) DONE"
