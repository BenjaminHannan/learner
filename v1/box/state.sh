#!/bin/bash
# One state-lab arm on one box (run by the rent wrapper, kind state). Env from the wrapper: ROOT J PY DPH BOX_START RUN_END. Arm-specific env set
# by the pack's ARM.env (ARM=base|inject|reg16|mq4|lastloss, STEPS, CAP, SEED). Trains D alone (v1/state_lab.py), then runs the diagnostics.
# Everything lands in $ROOT/out/$ARM: final.json diag.json dev_evals.jsonl D-final.pt (+ the identical D-final.weights, see below), ckpt/, logs.
set -u
cd "$ROOT" || exit 1
. "$ROOT/ARM.env"                      # ARM, STEPS, CAP, SEED
SEED=${SEED:-0}
export PYTHONPATH="$ROOT" PYTHONHASHSEED=0
C="$J/checks"; O="$ROOT/out/$ARM"; mkdir -p "$C" "$O"
say() { echo "=== $* $(date -u +%FT%TZ)"; }
CORES=$(nproc); W=$(( CORES < 16 ? CORES : 16 ))
say "STEP data (train 380 + dev 20 shards + validation; the sealed test split is NOT built here), workers $W"
$PY -m v1.box_build "$J/data/v1village" --train-shards 380 --dev-shards 20 --workers "$W" > "$C/box_build.out" 2>&1 || { tail -5 "$C/box_build.out"; exit 1; }
tail -1 "$C/box_build.out"
# Time left for the whole job minus 25 min kept for the final eval, diag and export; a run cut off by this is a FAIL (checkpoints are still exported).
LEFT=$(( RUN_END - $(date +%s) - 1500 ))
[ "$LEFT" -gt 600 ] || { echo "only $LEFT s left for training"; exit 1; }
say "STEP train arm $ARM seed $SEED steps $STEPS at \$$DPH/h, cap \$$CAP, train budget ${LEFT}s"
timeout "$LEFT" $PY -m v1.state_lab train --arm "$ARM" --seed "$SEED" --root "$J/data/v1village" --out "$O" --steps "$STEPS" --workers "$W" 2>&1 | tee -a "$C/train_$ARM.out"
RC=${PIPESTATUS[0]}
echo "train $ARM rc=$RC"
[ "$RC" = 0 ] || exit "$RC"
[ -f "$O/D-final.pt" ] || { echo "no D-final.pt"; exit 1; }
# out.tar.gz skips *.pt (weights travel in ckpt.tar.gz); keep a second copy under another name so ANY pull of out.tar.gz has the weights too.
cp "$O/D-final.pt" "$O/D-final.weights"
say "STEP diag arm $ARM"
$PY -m v1.state_lab diag --ckpt "$O/D-final.pt" --root "$J/data/v1village" --out "$O/diag.json" --workers "$W" 2>&1 | tee -a "$C/diag_$ARM.out"
RC=${PIPESTATUS[0]}
echo "diag $ARM rc=$RC"
[ -f "$O/final.json" ] && head -c 3000 "$O/final.json"
exit "$RC"
