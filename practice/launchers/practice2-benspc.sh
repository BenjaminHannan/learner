#!/usr/bin/env bash
# Practice-2 full run, knights_knaves (PREREG-2 + addenda 1-4), on BensPC (RTX 5070 Ti 16 GB, WSL Ubuntu, ~/bbvenv), through the OpenCode harness (addendum 1).
# Tries: vLLM (own venv ~/.cache/practice2_vllm_env) + practice/k2_proxy. Nights: HF QLoRA with an NF4 base (--nf4, same as the Mac pilots' q4 nights), capped at 14 GiB
# so WSL raises a real OOM instead of spilling into system memory and crawling. Every phase is resumable: re-running on the same OUT continues.
#
# Slot (coordinator 11:09Z Oct 27): WAIT for C:\Users\benja\pc-jobs\handoff\GO-AFTER-RECALLREAD (Notebook-2 writes it even if recallread fails) and a free GPU.
# When this run ends, for any reason after it started, write handoff\GO-AFTER-PRACTICE2 (the 8 GB thread's K1 follows).
#
#   detached launch (pc-launch-route): pc-ps 'Invoke-CimMethod Win32_Process -MethodName Create -Arguments @{CommandLine="wsl.exe -d Ubuntu -e bash /mnt/c/Users/benja/pc-jobs/practice2/practice2-benspc.sh"}'
#
# Env: SRC (unpacked `git archive <sha> practice sleep2`, default ~/practice2/src), OUT, SKILLS, PORT, CONC, TRAIN_TOKENS, CAP_GIB.
# Downloads on first run if missing: vLLM venv (~4 GB; skipped when VLLM_PY or ~/vllmvenv already has vllm), Node 22 (~30 MB), opencode-ai (~100 MB), reasoning-gym, bitsandbytes. Not on the phone hotspot.
set -uo pipefail
WIN=/mnt/c/Users/benja
HAND="$WIN/pc-jobs/handoff"
GO_IN="$HAND/GO-AFTER-RECALLREAD"
GO_OUT="$HAND/GO-AFTER-PRACTICE2"
BUSY="$WIN/GPU-BUSY.txt"
CARD="$WIN/pc-jobs/practice2.md"
SRC="${SRC:-$HOME/practice2/src}"
SKILLS="${SKILLS:-knights_knaves}"
OUT="${OUT:-$HOME/practice2/out-$SKILLS}"
PORT="${PORT:-18081}"
CONC="${CONC:-16}"
TRAIN_TOKENS="${TRAIN_TOKENS:-6144}"
export PRACTICE_CUDA_CAP_GIB="${CAP_GIB:-14}"
NVSMI="$(command -v nvidia-smi || echo /usr/lib/wsl/lib/nvidia-smi)"
mkdir -p "$OUT" "$HAND"
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$OUT/job.log"; }

# ---- wait for the slot: the flag, no other GPU-BUSY owner, < 1.5 GB in use on the card for 2 checks in a row
log "waiting for $GO_IN and a free GPU"
ok=0
while :; do
  used=$("$NVSMI" --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -dc 0-9)
  if [ -f "$GO_IN" ] && { [ ! -s "$BUSY" ] || grep -q practice2 "$BUSY"; } && [ -n "$used" ] && [ "$used" -lt 1500 ]; then
    ok=$((ok + 1)); [ "$ok" -ge 2 ] && break
  else
    ok=0
  fi
  sleep 60
done
log "slot is ours (GPU used ${used} MiB)"

printf 'practice2 (Let the model practice puzzles, then sleep) since %s\n' "$(date -u +%FT%TZ)" > "$BUSY"
printf '# practice2\nthread: Let the model practice puzzles, then sleep\nstarted: %s\nskills: %s\nlog: %s\nnext: writes %s when done\n' \
  "$(date -u +%FT%TZ)" "$SKILLS" "$(wslpath -w "$OUT/job.log" 2>/dev/null || echo "$OUT/job.log")" "$(wslpath -w "$GO_OUT" 2>/dev/null || echo "$GO_OUT")" > "$CARD"
finish() {
  rc=$?
  pkill -f "vllm.entrypoints" 2>/dev/null || true
  rm -f "$BUSY" "$CARD"
  printf 'practice2 %s ended rc=%s at %s\n' "$SKILLS" "$rc" "$(date -u +%FT%TZ)" > "$GO_OUT"
  log "ended rc=$rc; wrote $GO_OUT"
}
trap finish EXIT
set -e

test -f "$SRC/practice/job.py" && test -f "$SRC/practice/oc_cuda.py"
cd "$SRC"
# shellcheck disable=SC1090
source "$HOME/bbvenv/bin/activate"
export PYTHONPATH="$SRC${PYTHONPATH:+:$PYTHONPATH}"
unset PYTORCH_CUDA_ALLOC_CONF   # expandable segments broke K2 training under WSL (pc-launch-route)
log "practice2 (opencode, vLLM) skills=$SKILLS src=$(cat "$SRC/COMMIT" 2>/dev/null || echo ?)"

python -c "import reasoning_gym" 2>/dev/null || pip install -q "reasoning-gym==0.1.25"
python -c "import bitsandbytes" 2>/dev/null || pip install -q bitsandbytes

# vLLM only serves (vllm serve + LoRA), so any venv where `import vllm` works will do; an existing one is used read-only (nothing is installed into it).
VPY=""
for c in "${VLLM_PY:-}" "$HOME/.cache/practice2_vllm_env/bin/python" "$HOME/vllmvenv/bin/python"; do
  [ -n "$c" ] && [ -x "$c" ] && "$c" -c "import vllm" 2>/dev/null && { VPY="$c"; break; }
done
if [ -z "$VPY" ]; then
  VENV="${HOME}/.cache/practice2_vllm_env"
  VPY="$VENV/bin/python"
  [ -x "$VPY" ] || { (pip install -q uv && python -m uv venv "$VENV") 2>/dev/null || python -m venv "$VENV"; }
  (python -m uv pip install -q --python "$VPY" vllm 2>/dev/null) || timeout 2400 "$VPY" -m pip install -q vllm
fi
"$VPY" -c "import vllm, torch; print('vllm', vllm.__version__, 'torch', torch.__version__, torch.cuda.get_device_capability(0))" 2>&1 | tee -a "$OUT/job.log"
export VLLM_PY="$VPY"

NODE_HOME="${HOME}/.cache/node22"
if ! command -v node >/dev/null 2>&1 || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]; then
  if [ ! -x "$NODE_HOME/bin/node" ]; then
    python - "$NODE_HOME" <<'PY'
import sys, tarfile, tempfile, urllib.request
dest, ver = sys.argv[1], "v22.11.0"
url = f"https://nodejs.org/dist/{ver}/node-{ver}-linux-x64.tar.xz"
with tempfile.NamedTemporaryFile(suffix=".tar.xz") as f:
    urllib.request.urlretrieve(url, f.name)
    with tarfile.open(f.name, "r:xz") as t:
        members = [m for m in t.getmembers() if "/" in m.name]
        for m in members:
            m.name = m.name.split("/", 1)[1]
        t.extractall(dest, members=members)
PY
  fi
  export PATH="$NODE_HOME/bin:$PATH"
fi
NPM_PREFIX="${HOME}/.cache/practice2_npm"
export PATH="$NPM_PREFIX/bin:$PATH"
opencode --version 2>/dev/null | grep -q '^1\.19\.4' || npm install -g --prefix "$NPM_PREFIX" opencode-ai@1.19.4 2>&1 | tail -3 | tee -a "$OUT/job.log"
log "node $(node --version) opencode $(opencode --version)"
python -m practice.oc_cuda --warm 2>&1 | tee -a "$OUT/job.log"
test "${PIPESTATUS[0]}" -eq 0

# addendum 4: 500 puzzles x 4 tries per day, 3 days; 300-puzzle test x 2 tries; evals after nights 1 and 3
python -m practice.job --rg-skills "$SKILLS" --out "$OUT" --backend auto --harness opencode --nf4 --oc-port "$PORT" \
  --oc-concurrency "$CONC" --oc-util 0.85 --oc-max-len 12288 --oc-max-seqs 32 --oc-train-tokens "$TRAIN_TOKENS" \
  --rg-day-n 500 --tries 4 --rg-test-n 300 --test-tries 2 --nights 3 --eval-nights 1,3 2>&1 | tee -a "$OUT/run.log"
test "${PIPESTATUS[0]}" -eq 0
python -m practice.analyze_rg "$OUT" --night 3 > "$OUT/verdicts.json" || true
log "done"
