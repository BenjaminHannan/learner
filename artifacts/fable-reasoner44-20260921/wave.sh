#!/bin/bash
# Experiment 44 registered wave.  Run from the worktree root:
#     bash artifacts/fable-reasoner44-20260921/wave.sh
# Three seeds side by side (3 single-thread processes at a time), every stage offline on CPU.
set -eu
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/artifacts/fable-reasoner44-20260921/runs"
LOGS="$ROOT/artifacts/fable-reasoner44-20260921/logs"
PY="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
SEEDS="4102 4103 4104"
mkdir -p "$OUT" "$LOGS"
cd "$ROOT"

echo "== stage base =="
for s in $SEEDS; do
  $PY scripts/fable_reasoner44.py --stage base --seed "$s" --out "$OUT" >"$LOGS/base-seed$s.log" 2>&1 &
done
wait
for s in $SEEDS; do cat "$LOGS/base-seed$s.log"; done

echo "== stage sleep, 20 episodes (+ random and 10%-wrong controls) =="
for s in $SEEDS; do
  $PY scripts/fable_reasoner44.py --stage sleep --seed "$s" --episodes 20 --out "$OUT" >"$LOGS/sleep-seed$s-ep20.log" 2>&1 &
done
wait
for s in $SEEDS; do cat "$LOGS/sleep-seed$s-ep20.log"; done

echo "== stage sleep, 50 episodes =="
for s in $SEEDS; do
  $PY scripts/fable_reasoner44.py --stage sleep --seed "$s" --episodes 50 --out "$OUT" >"$LOGS/sleep-seed$s-ep50.log" 2>&1 &
done
wait
for s in $SEEDS; do cat "$LOGS/sleep-seed$s-ep50.log"; done

echo "== wave done =="
