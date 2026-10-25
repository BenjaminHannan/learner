#!/usr/bin/env bash
# Speed box job (run from the unpacked tree by speed/box/vast_speed.py's job wrapper):  bash speed/box/run_speed_box.sh
# One Vast RTX PRO 6000 (95 GB): download Qwen3.6-35B-A3B once (HF cache), then three benches back to back, each under `timeout`,
# a failure never stops the next. Results: /job/out/speed_all.json (rewritten after every bench), logs /job/out/*.log.
# Order: mem (eager, then fused dequant) -> step (full 40-layer model) -> dreamgen. Hard limit 85 min from start, then self-stop.
set -u
cd "$(dirname "$0")/../.."
ROOT=$(pwd); OUT=/job/out; mkdir -p "$OUT"; ln -sfn "$OUT" "$ROOT/out"
exec > >(tee -a "$OUT/run_box.log") 2>&1
T0=$SECONDS; LIMIT=$((85*60))
REPO_ID=Qwen/Qwen3.6-35B-A3B; REV=995ad96eacd98c81ed38be0c5b274b04031597b0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
echo "== speed box $(date -u +%FT%TZ)"; nvidia-smi --query-gpu=name,memory.total --format=csv || echo "no nvidia-smi"; df -h /root /job | cat

self_stop() {
  python3 - <<'PY' || true
import os, urllib.request
r = urllib.request.Request("https://console.vast.ai/api/v0/instances/" + os.environ["CONTAINER_ID"] + "/", data=b'{"state": "stopped"}',
    method="PUT", headers={"Authorization": "Bearer " + os.environ["CONTAINER_API_KEY"], "Content-Type": "application/json"})
print(urllib.request.urlopen(r, timeout=30).read()[:200])
PY
}

# ---- merge: every *.json below is a bench's own partial/final file; speed_all.json is rebuilt from them after each bench
cat > /tmp/merge.py <<'PY'
import json, os, sys, time
O = "/job/out"
def load(n):
    try: return json.load(open(f"{O}/{n}"))
    except Exception as e: return {"missing_or_unreadable": repr(e)[:200]} if os.path.exists(f"{O}/{n}") else None
st = {}
try: st = json.load(open(f"{O}/status.json"))
except Exception: pass
res = {"schema": "speed_all-1", "wall_s": time.time() - float(os.environ.get("T_START", time.time())), "status": st, "env": load("env.json"),
       "mem_eager": load("mem_eager.json"), "mem_fused": load("mem_fused.json"), "step": load("step.json"), "step_fallback": load("step_fallback.json"), "dreamgen": load("dreamgen.json")}
json.dump(res, open(f"{O}/speed_all.json.tmp", "w"), indent=1, default=str); os.replace(f"{O}/speed_all.json.tmp", f"{O}/speed_all.json")
PY
export T_START=$(date +%s)
merge() { python3 /tmp/merge.py || echo "!! merge failed"; }
note() { python3 - "$1" "$2" <<'PY'
import json, sys
p = "/job/out/status.json"
try: d = json.load(open(p))
except Exception: d = {}
d[sys.argv[1]] = sys.argv[2]
json.dump(d, open(p, "w"), indent=1)
PY
}
finish() { echo "== finish $(date -u +%FT%TZ) elapsed $((SECONDS-T0))s"; merge; ls -la "$OUT"; echo "=== BB DONE speed $(date -u +%FT%TZ)"; exit 0; }
trap finish TERM
( sleep $LIMIT; echo "!! 85-min hard limit"; note watchdog "hard limit hit"; merge; self_stop ) &
WD=$!
left() { echo $((LIMIT - (SECONDS - T0))); }

# ---- installs (pinned to the A11 Qwen3.6 box env) in parallel with the model download
pip install -q "huggingface_hub==2.3.0" "hf_xet==1.7.0" || pip install -q huggingface_hub hf_xet
(
  python3 - <<PY
import time, os
from huggingface_hub import snapshot_download
t = time.time()
for i in range(4):
    try:
        p = snapshot_download("$REPO_ID", revision="$REV", max_workers=16, allow_patterns=["*.json", "*.safetensors", "*.py", "*.jinja", "*.txt", "*.model", "tokenizer*"])
        break
    except Exception as e:
        print("download retry", i, repr(e)[:200], flush=True); time.sleep(10)
else:
    raise SystemExit("download failed")
# scripts that do not pass the revision (profile_step, gpu_bench) resolve refs/main: point it at the pinned snapshot
ref = os.path.join(os.path.dirname(os.path.dirname(p)), "refs"); os.makedirs(ref, exist_ok=True)
open(os.path.join(ref, "main"), "w").write("$REV")
print("download done", p, round(time.time() - t), "s", flush=True)
PY
  echo $? > "$OUT/download.rc"
) > "$OUT/download.log" 2>&1 &
DL=$!
python3 -m pip install -q "transformers==5.20.2" "peft==0.21.2" "accelerate==1.15.0" "flash-linear-attention==0.6.0" datasets || echo "!! pip install failed"
python3 - <<'PY' | tee "$OUT/env.txt"
import json, sys, importlib.metadata as m
d = {"python": sys.version.split()[0]}
for p in ("torch", "transformers", "peft", "accelerate", "huggingface_hub", "hf_xet", "flash-linear-attention", "triton", "datasets"):
    try: d[p] = m.version(p)
    except Exception: d[p] = None
import torch
d.update(cuda=torch.cuda.is_available(), gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
         gpu_gib=round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2) if torch.cuda.is_available() else None)
try:
    import fla; d["fla_importable"] = True
except Exception as e: d["fla_importable"] = repr(e)[:100]
json.dump(d, open("/job/out/env.json", "w"), indent=1); print(json.dumps(d))
PY
echo "installs done at $((SECONDS-T0))s; waiting for download"
wait $DL
echo "download+installs done at $((SECONDS-T0))s"; cat "$OUT/download.log" | tail -3
if [ "$(cat "$OUT/download.rc" 2>/dev/null)" != 0 ]; then note download "FAILED"; merge; echo "!! no model, nothing to bench"; kill $WD 2>/dev/null; finish; fi
note download_done_s "$((SECONDS-T0))"; merge
export HF_HUB_OFFLINE=1   # everything is in the cache now; no accidental second download

# run NAME MINUTES -- cmd...   : timeout capped by the time left (minus 3 min for merge/stop), rc recorded, never fatal
run() {
  local name=$1 mins=$2; shift 3
  local cap=$(( $(left) - 180 )); local t=$(( mins*60 )); [ $cap -lt $t ] && t=$cap
  if [ $t -lt 120 ]; then note "$name" "skipped: only ${t}s left"; echo "-- skip $name"; return 0; fi
  echo "-- $name start $(date -u +%T) timeout ${t}s (elapsed $((SECONDS-T0))s): $*"
  local s=$SECONDS
  timeout -k 30 $t "$@" > "$OUT/$name.log" 2>&1; local rc=$?
  note "$name" "rc=$rc after $((SECONDS-s))s"; echo "-- $name rc=$rc after $((SECONDS-s))s"; tail -3 "$OUT/$name.log"
  merge; nvidia-smi --query-gpu=memory.used --format=csv,noheader; return $rc
}

# 1. mem: packed vs qdq. Eager dequant first (qdq reference + packed), then fused dequant (packed + packed_fit 32 GB emulation). ~12 min each.
run mem_eager 14 -- python3 speed/qwen36_mem/bench_mem.py --out "$OUT/mem_eager.json" --modes qdq,packed
run mem_fused 14 -- python3 speed/qwen36_mem/bench_mem.py --out "$OUT/mem_fused.json" --modes packed,packed_fit --compile-dequant
# 2. step: full 40-layer model (65 GB bf16 fits the 95 GB card at tok 2048); if that fails, 16 layers
run step 14 -- python3 speed/qwen36_step/profile_step.py --layers 40 --steps 6 --warmup 2 --out "$OUT/step.json" --work /tmp/qwen36_step_work
if [ $? -ne 0 ] && ! grep -q '"wall_s_per_step"' "$OUT/step.json" 2>/dev/null; then
  run step_fallback 8 -- python3 speed/qwen36_step/profile_step.py --layers 16 --steps 6 --warmup 2 --out "$OUT/step_fallback.json" --work /tmp/qwen36_step_work
fi
# 3. dreamgen: 64 prompts per phase, batch 32, five phases x four variants
run dreamgen 12 -- python3 speed/dreamgen/gpu_bench.py --model "$REPO_ID" --n 64 --bs 32 --out "$OUT/dreamgen.json"

kill $WD 2>/dev/null
finish
