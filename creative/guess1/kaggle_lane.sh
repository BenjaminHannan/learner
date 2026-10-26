#!/bin/bash
# Guess-1 on a Kaggle 2x T4 box: serve K2-Horizon-3.7B (fp16, thinking off) with vLLM, one server per T4 behind a
# tiny round-robin proxy, then run Guess-1. Usage: bash kaggle_lane.sh OUT [smoke|full]
#   smoke: 4 tasks x 8 screen tries, prints episodes/min and how many replies carried parsed tool calls, then exits.
#   full:  `run.py all` (screen -> pick -> arms -> topup -> report). Stops launching episodes after 10 h (resumable).
set -uo pipefail
OUT=${1:?out dir}; MODE=${2:-smoke}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"; exec > >(tee -a "$OUT/lane.log") 2>&1
echo "$(date -u +%FT%TZ) mode=$MODE"; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv

# vLLM in its own venv so its torch never clashes with Kaggle's preinstalled torchaudio/torchvision (try 1 failed on
# exactly that); --torch-backend=auto picks the torch CUDA build that matches the installed driver.
pip install -q -U uv >/dev/null 2>&1; uv pip install --system -q httpx >/dev/null 2>&1
VV=/tmp/vllm-venv
[ -x $VV/bin/vllm ] || { uv venv -q --python 3.12 $VV && VIRTUAL_ENV=$VV uv pip install -q vllm --torch-backend=auto 2>&1 | tail -3; }

$VV/bin/python -c "import vllm, torch; print('vllm', vllm.__version__, 'torch', torch.__version__, 'cuda ok', torch.cuda.is_available())" 2>&1 | tail -1 | tee "$OUT/backend.txt"

serve() {  # $1 gpu, $2 port, $3 extra flags
  CUDA_VISIBLE_DEVICES=$1 $VV/bin/vllm serve IFM/K2-Horizon-3.7B --served-model-name k2 --port $2 --dtype float16 \
    --max-model-len 16384 --gpu-memory-utilization 0.90 --trust-remote-code --enforce-eager --enable-auto-tool-choice \
    --tool-call-parser k2_horizon --chat-template "$HERE/k2_nothink.jinja" $3 > "$OUT/vllm_$1.log" 2>&1 &
}
up() { for i in $(seq 90); do curl -sf localhost:$1/v1/models >/dev/null && return 0; sleep 10; done; return 1; }
serve 0 8001 ""; up 8001 || { echo "native vLLM failed on GPU0, retrying with --model-impl transformers"
  grep -E "Error" "$OUT/vllm_0.log" | tail -5; pkill -9 -f "vllm|EngineCore"; sleep 10
  cp "$OUT/vllm_0.log" "$OUT/vllm_0_native.log"
  IMPL="--model-impl transformers"; serve 0 8001 "$IMPL"; up 8001 || { echo "SERVE FAILED"; grep -E "Error" "$OUT/vllm_0.log" | tail -8; exit 1; }; }
echo "impl: ${IMPL:-native}" >> "$OUT/backend.txt"
serve 1 8002 "${IMPL:-}"; up 8002 && PORTS="8001,8002" || PORTS="8001"
echo "ports $PORTS" | tee -a "$OUT/backend.txt"

# round-robin proxy on :8080 so the harness keeps a single base URL
python3 - "$PORTS" > "$OUT/proxy.log" 2>&1 <<'EOF' &
import sys, itertools, asyncio, httpx
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
ports = itertools.cycle(sys.argv[1].split(","))
cl = httpx.Client(timeout=600)
class H(BaseHTTPRequestHandler):
    def _go(self, method):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) if method == "POST" else None
        r = cl.request(method, f"http://127.0.0.1:{next(ports)}{self.path}", content=body, headers={"Content-Type": "application/json"})
        self.send_response(r.status_code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(r.content)
    def do_GET(self): self._go("GET")
    def do_POST(self): self._go("POST")
    def log_message(self, *a): pass
ThreadingHTTPServer(("127.0.0.1", 8080), H).serve_forever()
EOF
sleep 3; curl -sf localhost:8080/v1/models >/dev/null || { echo "PROXY FAILED"; cat "$OUT/proxy.log"; exit 1; }

ARGS=(--base-url http://127.0.0.1:8080/v1 --model k2 --concurrency 48)
cd "$HERE"
if [ "$MODE" = smoke ]; then
  T0=$(date +%s); python3 run.py screen "${ARGS[@]}" --out "$OUT/smoke" --limit 8
  python3 - "$OUT/smoke/results.jsonl" "$(( $(date +%s) - T0 ))" <<'EOF'
import sys, json
rows = [json.loads(l) for l in open(sys.argv[1])]; s = int(sys.argv[2])
tc = sum(1 for r in rows for m in r["transcript"] if m["role"] == "assistant" and m.get("tool_calls"))
asst = sum(1 for r in rows for m in r["transcript"] if m["role"] == "assistant")
print(f"SMOKE episodes={len(rows)} in {s}s = {len(rows)/max(s,1)*60:.1f}/min; successes={sum(r['success'] for r in rows)}; "
      f"assistant turns with tool calls {tc}/{asst}; projected full run ~{4000/max(len(rows)/max(s,1)*60,0.1)/60:.1f} h")
for r in rows[:2]: print(json.dumps(r["transcript"][:3])[:1500])
EOF
  exit 0
fi
timeout 36000 python3 run.py all "${ARGS[@]}" --out "$OUT/run"
python3 run.py report "${ARGS[@]}" --out "$OUT/run"
echo "$(date -u +%FT%TZ) DONE"; tail -40 "$OUT/run/report.md" 2>/dev/null
# Doubt Forks Step 0 gate on the same server (CPU-side analysis + prefill/greedy calls). Guarded: a crash here never touches the Guess-1 outputs above.
if [ -f "$OUT/run/results.jsonl" ] && [ -f "$OUT/run/target.json" ]; then
  ( cd "$HERE/../doubtforks" && uv pip install --system -q transformers >/dev/null 2>&1; timeout 7200 python3 step0.py --results "$OUT/run/results.jsonl" --base-url http://127.0.0.1:8080/v1 --model k2 --tokenizer IFM/K2-Horizon-3.7B --out "$OUT/df_step0" ) > "$OUT/df_step0.log" 2>&1 \
    || echo "df_step0 FAILED (Guess-1 outputs are intact), see $OUT/df_step0.log"
  tail -5 "$OUT/df_step0.log"; head -12 "$OUT/df_step0/gate.md" 2>/dev/null
fi
