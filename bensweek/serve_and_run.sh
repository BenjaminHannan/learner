#!/usr/bin/env bash
# Serve one model with vLLM and run the dev split against it, once per memory mode.
# Usage: bensweek/serve_and_run.sh OUT_DIR REPO "VLLM_ARGS" 'EXTRA_BODY_JSON' "notes none" [MAX_TOKENS]
# Resumable: rerunning skips finished tasks (--resume). Run from the repo root.
set -uo pipefail
OUT=$1; REPO=$2; VARGS=$3; EXTRA=${4:-'{}'}; MEMS=${5:-"notes none"}; MAXTOK=${6:-4096}
mkdir -p "$OUT"
python3 -c "import vllm" 2>/dev/null || pip install -q --user vllm 2>&1 | tail -2
python3 -c "import vllm; print('vllm', vllm.__version__)" | tee "$OUT/versions.txt"
git rev-parse HEAD >> "$OUT/versions.txt"

# shellcheck disable=SC2086
vllm serve "$REPO" --served-model-name m --port 8000 --max-model-len ${MAXLEN:-32768} \
  --gpu-memory-utilization ${GPU_UTIL:-0.90} --enable-auto-tool-choice $VARGS > "$OUT/vllm.log" 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null; sleep 5; pkill -9 -f EngineCore 2>/dev/null' EXIT
for i in $(seq 1 180); do
  curl -sf http://127.0.0.1:8000/v1/models >/dev/null && break
  kill -0 $SRV 2>/dev/null || { echo "vllm died"; tail -n 60 "$OUT/vllm.log"; exit 1; }
  sleep 10
done
curl -sf http://127.0.0.1:8000/v1/models >/dev/null || { echo "vllm never came up"; tail -n 60 "$OUT/vllm.log"; exit 1; }

rc=0
for mem in $MEMS; do
  python3 -m bensweek.run --agent openai --base-url http://127.0.0.1:8000/v1 --model m \
    --extra-body "$EXTRA" --memory "$mem" --concurrency 7 --max-tokens "$MAXTOK" \
    --out "$OUT/bw_$mem" --resume 2>&1 | tee -a "$OUT/run_$mem.log" || rc=1
done
exit $rc
