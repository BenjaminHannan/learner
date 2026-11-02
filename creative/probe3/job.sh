#!/usr/bin/env bash
# Probe-3 on one Kaggle T4 (PREREG.md): build the Haiku-imitation set (CPU), LoRA-train K2-3.7B, merge the adapter, serve the merged model (fp16, thinking off),
# K2+LoRA writes 4 probe samples per target task (with the start state, as Probe-2), analyze with the Probe-3 marks.
# Usage: job.sh RESULTS_DIR PICK1_K2_SCORES DATA_DIR OUT
#   RESULTS_DIR: Guess-1 seed-2 run dir (results.jsonl + target.json); PICK1_K2_SCORES: Pick-1 k2_scores.jsonl (SELF);
#   DATA_DIR: holds haiku_train_probes.jsonl (Haiku batch output; optional probes_haiku.jsonl = Haiku probes on the target tasks, diagnostics only).
# DTYPE=float16 (default; adds --enforce-eager) or DTYPE=bfloat16 on a 4090. Resumable: skips training if OUT/train/adapter exists, merging if OUT/merged exists.
# Serving: the adapter is merged into the base weights and the merged model is served (not --enable-lora): vLLM LoRA support for the custom k2_horizon class is untested
# on a T4, and a merged model takes exactly the Probe-2 serving path; the merge is exact up to fp16 rounding.
set -uo pipefail
SRC=${1:?results dir}; SELF=${2:?Pick-1 k2_scores.jsonl}; DATA=${3:?data dir with haiku_train_probes.jsonl}; OUT=${4:?out}
HERE=$(cd "$(dirname "$0")" && pwd); P1=$HERE/../probe1; DTYPE=${DTYPE:-float16}
[ -s "$SELF" ] || { echo "missing Pick-1 SELF scores: $SELF"; exit 4; }
[ -s "$DATA/haiku_train_probes.jsonl" ] || { echo "missing $DATA/haiku_train_probes.jsonl"; exit 4; }
mkdir -p "$OUT"; SELF=$(readlink -f "$SELF"); SRC=$(readlink -f "$SRC"); DATA=$(readlink -f "$DATA"); OUT=$(readlink -f "$OUT"); exec > >(tee -a "$OUT/job.log") 2>&1
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
python3 -m pip install -q --user httpx uv peft accelerate "transformers>=5.4" 2>&1 | tail -2
export PATH="$HOME/.local/bin:$PATH"
cd "$HERE"
python3 ../pick1/pools.py --results "$SRC" --out "$OUT/pools.jsonl" || exit 3
(cd "$P1" && python3 replay.py --check --results "$SRC") || { echo "REPLAY GATE FAILED"; exit 5; }
python3 build_data.py --haiku "$DATA/haiku_train_probes.jsonl" --results "$SRC" --out "$OUT/data" | tee "$OUT/build_data.txt" || exit 6
if [ ! -d "$OUT/train/adapter" ]; then
  python3 train_lora.py --data "$OUT/data" --out "$OUT/train" --dtype "$DTYPE" --merge-to "$OUT/merged.tmp" || { echo "TRAIN FAILED"; exit 7; }
  rm -rf "$OUT/merged"; mv "$OUT/merged.tmp" "$OUT/merged"
fi
[ -f "$OUT/merged/config.json" ] || { echo "NO MERGED MODEL (delete $OUT/train to retrain)"; exit 7; }
pkill -f "[v]llm serve" 2>/dev/null; sleep 2
VV=/tmp/guess1-vllm   # same venv path as the Guess-1 / Pick / Probe lanes, reused if present
[ -x $VV/bin/vllm ] || { python3 -m uv venv $VV && timeout 1500 python3 -m uv pip install --python $VV/bin/python vllm 2>&1 | tail -5; }
[ -x $VV/bin/vllm ] || { echo "VLLM INSTALL FAILED"; exit 2; }
EAGER=""; [ "$DTYPE" = float16 ] && EAGER="--enforce-eager"
$VV/bin/vllm serve "$OUT/merged" --served-model-name probe --port 8090 --dtype "$DTYPE" $EAGER --max-model-len 16384 \
  --gpu-memory-utilization ${GPU_UTIL:-0.85} --trust-remote-code --enable-auto-tool-choice --tool-call-parser k2_horizon \
  --chat-template "$HERE/../guess1/k2_nothink.jinja" > "$OUT/vllm.log" 2>&1 &
SP=$!; trap 'kill $SP 2>/dev/null; pkill -f "[v]llm serve" 2>/dev/null' EXIT
for i in $(seq 90); do curl -sf localhost:8090/v1/models >/dev/null && break; sleep 10; done
curl -sf localhost:8090/v1/models >/dev/null || { echo "SERVE FAILED"; grep Error "$OUT/vllm.log" | tail -8; exit 1; }
for pass in 1 2; do   # second pass resumes after transient failures
  (cd "$P1" && PROBE_WITH_STATE=1 python3 write_probes.py --results "$SRC" --base-url http://127.0.0.1:8090/v1 --model probe --concurrency ${CONC:-16} --out "$OUT/probes_probe3.jsonl")
done
kill $SP 2>/dev/null; pkill -f "[v]llm serve" 2>/dev/null
(cd "$P1" && python3 analyze.py --pools "$OUT/pools.jsonl" --results "$SRC" --k2 "$SELF" --probes "$OUT/probes_probe3.jsonl" --haiku-probes "$DATA/probes_haiku.jsonl" --wrong-at 37.5 --out "$OUT")
echo "$(date -u +%FT%TZ) DONE"
