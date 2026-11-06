#!/usr/bin/env bash
# Run from repo root on the Vast box. Env: SMALL, BIG, VLLM, LIMIT (optional).
set -euo pipefail
mkdir -p out
exec > >(tee -a out/run_box.log) 2>&1
nvidia-smi || true
if [ ! -f out/.installed ]; then
  pip install "vllm==${VLLM:-0.32.0}" datasets
  touch out/.installed
fi
python3 -c "import hf_transfer" 2>/dev/null && export HF_HUB_ENABLE_HF_TRANSFER=1 || true
SMALL=${SMALL:-Qwen/Qwen3.5-4B}
BIG=${BIG:-Qwen/Qwen3.6-35B-A3B-FP8}
LIM=""; [ -n "${LIMIT:-}" ] && LIM="--limit $LIMIT"

if [ "${MODE:-}" = sheet1 ]; then  # instruction-sheet test (PREREG-sheet1.md): one model load, ~30 min
  python3 tricks/sheet1.py --model "${SMALL:-Qwen/Qwen3.5-4B}" --out out/sheet1 $LIM || echo "!! sheet1 failed"
  grep '^\[sum\]' out/sheet1/summary.txt | cut -c1-250 || true
  tar czf out.tar.gz out
  echo "[done] out.tar.gz"
  exit 0
fi

ONLY=${ONLY:-both}   # small | big | both (two boxes can split the work)
run() {  # model tag arms: one process for all arms (one model load), then per-arm retries; finished sets are skipped
  python3 tricks/tricks1.py --model "$1" --arms "$3" --out "out/$2" $LIM || echo "!! $3 ($2) failed"
  for arm in ${3//,/ }; do python3 tricks/tricks1.py --model "$1" --arms "$arm" --out "out/$2" $LIM || echo "!! $arm ($2) failed"; done
}
[ "$ONLY" = big ] || run "$SMALL" small s_plain,s_py,s_wiki,s_vote8,s_think
[ "$ONLY" = small ] || run "$BIG" big b_plain,b_wiki,b_think

python3 tricks/summarize.py out > out/SUMMARY.md || echo "!! summarize failed"
while IFS= read -r l; do echo "[sum] ${l:0:250}"; done < out/SUMMARY.md
tar czf out.tar.gz out
echo "[done] out.tar.gz"
