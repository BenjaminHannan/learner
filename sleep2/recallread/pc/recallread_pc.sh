#!/usr/bin/env bash
# Recall-then-read stage 1 on BensPC (RTX 5070 Ti 16 GB, WSL). Runs in WSL as Ben's user; launched detached by stage_mac.sh.
# Slot (coordinator, 2026-10-27 11:06Z): after sleep V8. Waits for $H/GO-AFTER-V8 and a free GPU (no GPU-BUSY.txt, under 4 GB used,
# twice 2 min apart); when it ends, even on failure, clears GPU-BUSY.txt and its card and writes "<rc> <time>" to $H/GO-AFTER-RECALLREAD
# (next in the PC order: Practice-2 knights_knaves).
# 16 GB deviations from gpuq-recallread.sh (4090 plan), all from the sleep thread's working K2 settings on this card (sleepb_pc7.sh):
#   Sleep-B code at 005265d6fb (not a7ed69d; the ab_ob_b4_nb defaults are unchanged, new flags default to "as before"),
#   SLEEPB_CUDA_CAP_GIB=14 with PyTorch's default allocator, --tok-budget 256 (not 1024), --gen-bs 24 (out of memory: again at 16),
#   seed 1 only here (seed 2 later on Kaggle/rented GPU; cheap tests first). Time budget 14 h for sleep; eval after.
set -uo pipefail
W=/mnt/c/Users/benja
H=$W/pc-jobs/handoff
J=${J:-$HOME/recallread-pc}
SRC=$J/src
R=$W/pc-jobs/recallread
OUT=$J/out
mkdir -p "$R" "$H" "$OUT"
exec >>"$R/run.log" 2>&1
export SLEEPB_CUDA_CAP_GIB=${SLEEPB_CUDA_CAP_GIB:-14} TOKENIZERS_PARALLELISM=false
unset PYTORCH_CUDA_ALLOC_CONF PYTORCH_ALLOC_CONF LEARNER_ANTHROPIC_API_KEY ANTHROPIC_API_KEY
source "$HOME/bbvenv/bin/activate"
gpu_used() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1; }
free_now() { [ ! -s "$W/GPU-BUSY.txt" ] && [ "$(gpu_used)" -lt 4000 ] 2>/dev/null; }
echo "== recallread-pc waiting for $H/GO-AFTER-V8 $(date -u +%FT%TZ)"
while :; do
  if [ -f "$H/GO-AFTER-V8" ] && free_now; then sleep 120; free_now && break; fi
  sleep 60
done
echo "== turn came $(date -u +%FT%TZ), GPU used $(gpu_used) MiB"
echo "recallread-pc (Close the diary search gap on the real model): started $(date -u +%FT%TZ)" > "$W/GPU-BUSY.txt"
printf '# recallread-pc\nowner: Close the diary search gap on the real model\nlog: C:\\Users\\benja\\pc-jobs\\recallread\\run.log\nends: writes GO-AFTER-RECALLREAD in C:\\Users\\benja\\pc-jobs\\handoff and removes this card and GPU-BUSY.txt\n' > "$W/pc-jobs/recallread-pc.md"
release() {
  grep -qs recallread-pc "$W/GPU-BUSY.txt" && rm -f "$W/GPU-BUSY.txt"
  rm -f "$W/pc-jobs/recallread-pc.md"
  echo "$1 $(date -u +%FT%TZ)" > "$H/GO-AFTER-RECALLREAD"
  echo "== released the GPU rc=$1 $(date -u +%FT%TZ)"
}
trap 'release 99' TERM INT
cd "$SRC"
export RR_BACKBONE="$SRC/backbone"
cat "$SRC/SHAS.txt" 2>/dev/null
python - <<'PY' || { release 2; exit 2; }
import torch, transformers, peft
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), "transformers", transformers.__version__, "peft", peft.__version__)
assert torch.cuda.is_available()
PY
FR=$SRC/data/recallread
[ "$(sha256sum "$FR/items.json" | cut -d' ' -f1)" = "$(cut -d' ' -f1 "$FR/items.sha256")" ] || { echo "STOP: items.json hash"; release 3; exit 3; }
[ "$(sha256sum "$FR/week2.json" | cut -d' ' -f1)" = "70db7146ed59d10cbd0d2e8d7a6fc0e245d4b07ec57add0c793db1fdff006e5b" ] || { echo "STOP: week2 hash"; release 3; exit 3; }
mem() { grep -qs "OutOfMemoryError\|CUDA out of memory\|device not ready" "$OUT/sleep/s1/sleepb.log"; }
sleep_try() {  # sleep_try GEN_BS
  echo "== phase 1: sleep seed 1 gen-bs $1 $(date -u +%FT%TZ)"
  timeout 14h python -m sleep2.recallread.train_sleep --backbone "$RR_BACKBONE" --week "$FR/week2.json" --out "$OUT" --seeds 1 --tok-budget 256 --gen-bs "$1"
}
sleep_try 24; rc=$?
if [ $rc -ne 0 ] && mem; then echo "== out of memory at gen-bs 24: again at 16"; rm -rf "$OUT/sleep/s1"; sleep_try 16; rc=$?; fi
mkdir -p "$R/pull"; cp -f "$OUT/sleep/s1/sleepb.log" "$OUT"/sleep/s1/result_*.json "$R/pull/" 2>/dev/null
if [ $rc -ne 0 ]; then echo "== sleep failed rc=$rc"; release $rc; exit $rc; fi
echo "== phase 2: eval $(date -u +%FT%TZ)"
python -m sleep2.recallread.run_eval --frozen "$FR" --out "$OUT/smoke" --limit 20 --adapter "1=$OUT/sleep/s1/adapter" --arms D0 R D3 || { rc=$?; echo "== smoke eval failed"; release $rc; exit $rc; }
rm -rf "$OUT/smoke"
timeout 6h python -m sleep2.recallread.run_eval --frozen "$FR" --out "$OUT" --adapter "1=$OUT/sleep/s1/adapter"; rc=$?
cp -rf "$OUT/results" "$R/pull/" 2>/dev/null
echo "== done rc=$rc $(date -u +%FT%TZ); results in $R/pull/results"
release $rc
