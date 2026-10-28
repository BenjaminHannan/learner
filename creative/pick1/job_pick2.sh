#!/usr/bin/env bash
# Pick-2 on one GPU (PREREG-pick2.md): serve K2-3.7B, rebuild pools with 1,500-char tool results, judge FULL (P(yes)) and THINK
# (low-effort thinking), analyze against RAND and Pick-1 SELF, print the Pick-2 verdict. No new episodes.
# Usage: job_pick2.sh RESULTS_DIR PICK1_K2_SCORES OUT
#   RESULTS_DIR: Guess-1 run dir (results.jsonl + target.json); PICK1_K2_SCORES: Pick-1 k2_scores.jsonl (SELF; required, no default).
# DTYPE=float16 (default; adds --enforce-eager) or DTYPE=bfloat16 on a 4090.
set -uo pipefail
SRC=${1:?results dir}; SELF=${2:?Pick-1 k2_scores.jsonl}; OUT=${3:?out}; HERE=$(cd "$(dirname "$0")" && pwd); DTYPE=${DTYPE:-float16}
[ -s "$SELF" ] || { echo "missing Pick-1 SELF scores: $SELF"; exit 4; }
mkdir -p "$OUT"; SELF=$(readlink -f "$SELF"); exec > >(tee -a "$OUT/job_pick2.log") 2>&1
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
python3 -m pip install -q --user httpx uv 2>&1 | tail -2
export PATH="$HOME/.local/bin:$PATH"
cd "$HERE"
python3 pools.py --results "$SRC" --cut 1500 --out "$OUT/pools_full.jsonl" || exit 3
VV=/tmp/guess1-vllm
[ -x $VV/bin/vllm ] || { python3 -m uv venv $VV && timeout 1500 python3 -m uv pip install --python $VV/bin/python vllm 2>&1 | tail -5; }
[ -x $VV/bin/vllm ] || { echo "VLLM INSTALL FAILED"; exit 2; }
EAGER=""; [ "$DTYPE" = float16 ] && EAGER="--enforce-eager"
# No --reasoning-parser: judge_k2 think mode reads reasoning_content + content together, so it works with or without one,
# and without it a truncated (unclosed) think block still lands in content where the parse can see it.
$VV/bin/vllm serve IFM/K2-Horizon-3.7B --served-model-name k2 --port 8090 --dtype "$DTYPE" $EAGER --max-model-len 16384 \
  --gpu-memory-utilization ${GPU_UTIL:-0.85} --trust-remote-code --enable-auto-tool-choice --tool-call-parser k2_horizon \
  --chat-template "$HERE/../guess1/k2_nothink.jinja" > "$OUT/vllm.log" 2>&1 &
SP=$!; trap 'kill $SP 2>/dev/null' EXIT
for i in $(seq 90); do curl -sf localhost:8090/v1/models >/dev/null && break; sleep 10; done
curl -sf localhost:8090/v1/models >/dev/null || { echo "SERVE FAILED"; grep Error "$OUT/vllm.log" | tail -8; exit 1; }
J="--base-url http://127.0.0.1:8090/v1 --model k2 --concurrency ${CONC:-32} --pools $OUT/pools_full.jsonl"
for pass in 1 2; do   # second pass resumes after transient failures
  python3 judge_k2.py $J --mode p_yes --out "$OUT/full_scores.jsonl"
  python3 judge_k2.py $J --mode think --out "$OUT/think_scores.jsonl"
done
python3 analyze.py --pools "$OUT/pools_full.jsonl" --k2 "$SELF" --out "$OUT" \
  --judge "FULL=$OUT/full_scores.jsonl:p_yes" --judge "THINK=$OUT/think_scores.jsonl:score" --pick2
echo "$(date -u +%FT%TZ) DONE"
