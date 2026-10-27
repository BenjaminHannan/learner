#!/usr/bin/env bash
# Run the dev split against Qwen3.6 (or another MLX model) on a Mac with mlx_lm.server.
# Usage: bensweek/mac_run.sh OUT_DIR [MODEL] [MEMS]
#   MODEL default mlx-community/Qwen3.6-35B-A3B-4bit, MEMS default "notes none".
#   PY=/path/to/python-with-mlx_lm (default: $ASSISTANT_PY, else python3). PORT default 18090.
# One model job at a time: refuses to start if PAUSE_OTHERS / ASSISTANT_RUNNING exist or another
# mlx/llama server is running. Thinking off (same as the gateway's qwen36-fast). Resumable.
set -uo pipefail
OUT=$1; MODEL=${2:-mlx-community/Qwen3.6-35B-A3B-4bit}; MEMS=${3:-"notes none"}
PY=${PY:-${ASSISTANT_PY:-python3}}; PORT=${PORT:-18090}
OPS=~/learner-ops
for f in "$OPS/PAUSE_OTHERS" "$OPS/ASSISTANT_RUNNING"; do
  [ -e "$f" ] && { echo "refusing: $f exists (Ben is using the Mac or jobs are paused)"; exit 2; }
done
if ps axo command= | grep -E "mlx_lm|mlx-lm|llama-server" | grep -v grep >/dev/null; then
  echo "refusing: another model server is running"; exit 2
fi
mkdir -p "$OUT"
"$PY" -c "import mlx_lm; print('mlx_lm', mlx_lm.__version__)" | tee "$OUT/versions.txt" || exit 1
git rev-parse HEAD >> "$OUT/versions.txt" 2>/dev/null

"$PY" -m mlx_lm.server --model "$MODEL" --host 127.0.0.1 --port "$PORT" \
  --max-tokens 4096 --prompt-cache-size 8 --prompt-cache-bytes 1GB > "$OUT/server.log" 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for i in $(seq 1 120); do
  curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null && break
  kill -0 $SRV 2>/dev/null || { echo "server died"; tail -n 40 "$OUT/server.log"; exit 1; }
  sleep 5
done

rc=0
for mem in $MEMS; do
  # mlx_lm.server only serves the loaded model; "default_model" avoids it trying to load another
  "$PY" -m bensweek.run --agent openai --base-url "http://127.0.0.1:$PORT/v1" --model default_model \
    --extra-body '{"chat_template_kwargs": {"enable_thinking": false}}' --memory "$mem" \
    --concurrency 2 --max-tokens 4096 --out "$OUT/bw_$mem" --resume 2>&1 | tee -a "$OUT/run_$mem.log" || rc=1
done
exit $rc
