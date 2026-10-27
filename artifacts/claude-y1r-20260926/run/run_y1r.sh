#!/usr/bin/env bash
# y1r, the one run (PLAN.md, ADDENDUM-1 order). Run from the repo root. Counts only.
set -uo pipefail
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONHASHSEED=0
PY="python3 -B"
D=artifacts/claude-y1r-20260926
I=artifacts/claude-y1t-20260926/glm2/items
S=/tmp/claude-0/-home-user-learner/1cfdffc0-c8e4-5383-b5bd-c255c25d9fcd/scratchpad/y1r/real
DATA=/tmp/claude-0/-home-user-learner/1cfdffc0-c8e4-5383-b5bd-c255c25d9fcd/scratchpad/y1r/data
OUT=$D/run
mkdir -p "$S" "$OUT"
st() { echo "== $1 $(date -u '+%F %T') UTC"; }
st start
echo "python: $(python3 --version); torch/transformers: $($PY -c 'import torch, transformers; print(torch.__version__, transformers.__version__)' 2>/dev/null)"
for s in SEAL-y1r SEAL-y1r-add1 SEAL-y1r-add2 SEAL-y1r-add3; do
  shasum -a 256 -c $D/$s.sha256.txt > /dev/null || { echo "SEAL-MISMATCH $s"; exit 5; }; echo "$s: all OK"
done
printf '%s  %s\n' 47e2e2955bf085816abcda50fdfc4230d0030cbe72b5d8df4109e704858c79e4 $I/items_train.jsonl \
  c0288f2cb7a5b764f974f49d1bfeb5b8ddb0de68e8ce63fffc6cc4d0a3d407e4 $I/items_dev.jsonl | shasum -a 256 -c - || { echo ITEMS-MISMATCH; exit 5; }
echo "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4  $DATA/locomo10.json" | shasum -a 256 -c - || { echo LOCOMO-MISMATCH; exit 5; }
$PY scripts/claude_y1r_retriever.py --selftest 2>&1 | tail -1
$PY scripts/claude_y1r_control.py --selftest 2>&1 | tail -1
st pairs
echo "pairs train: $($PY scripts/claude_y1r_retriever.py pairs --items $I/items_train.jsonl --out $S/pairs_train.jsonl)"
echo "pairs dev: $($PY scripts/claude_y1r_retriever.py pairs --items $I/items_dev.jsonl --out $S/pairs_dev.jsonl)"
echo "control: $($PY scripts/claude_y1r_control.py shuffle --pairs $S/pairs_train.jsonl --out $S/pairs_control.jsonl --seed 4037)"
st "train R"
$PY scripts/claude_y1r_retriever.py train --pairs $S/pairs_train.jsonl --dev $S/pairs_dev.jsonl --out $S/R > $S/train_R.log 2>&1; echo "train R rc=$?"; tail -2 $S/train_R.log
st "train C"
$PY scripts/claude_y1r_retriever.py train --pairs $S/pairs_control.jsonl --dev $S/pairs_dev.jsonl --out $S/C > $S/train_C.log 2>&1; echo "train C rc=$?"; tail -2 $S/train_C.log
st "locomo U"
$PY scripts/claude_y1r_retriever.py locomo --data $DATA --out $S/U > $S/locomo_U.log 2>&1; echo "locomo U rc=$?"; tail -1 $S/locomo_U.log
st "locomo R"
$PY scripts/claude_y1r_retriever.py locomo --data $DATA --out $S/LR --encoder $S/R/encoder.pt > $S/locomo_R.log 2>&1; echo "locomo R rc=$?"; tail -1 $S/locomo_R.log
st "locomo C"
$PY scripts/claude_y1r_retriever.py locomo --data $DATA --out $S/LC --encoder $S/C/encoder.pt > $S/locomo_C.log 2>&1; echo "locomo C rc=$?"; tail -1 $S/locomo_C.log
sha256sum $S/R/encoder.pt $S/C/encoder.pt $S/pairs_train.jsonl $S/pairs_dev.jsonl $S/pairs_control.jsonl
st end
