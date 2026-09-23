#!/bin/sh
# freeze -> wave -> summary.  One torch thread per worker process.
# Env: PY (interpreter), VARIANT, SEEDS, NAME, PARALLEL.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PY:-python3}
VARIANT=${VARIANT:-grow-blind}
SEEDS=${SEEDS:-100-147}
NAME=${NAME:-wave-1}
REL="$HERE/scripts/fable_operator_reliability.py"

OMP_NUM_THREADS=1; MKL_NUM_THREADS=1; OPENBLAS_NUM_THREADS=1
VECLIB_MAXIMUM_THREADS=1; NUMEXPR_NUM_THREADS=1; PYTHONDONTWRITEBYTECODE=1
PYTHONUTF8=1
export OMP_NUM_THREADS MKL_NUM_THREADS OPENBLAS_NUM_THREADS PYTHONUTF8
export VECLIB_MAXIMUM_THREADS NUMEXPR_NUM_THREADS PYTHONDONTWRITEBYTECODE

# Fail early and loudly if this torch cannot read panels written by a newer torch.
"$PY" -B "$HERE/scripts/fable_operator_reliability.py" verify --repo "$HERE" \
      --variant "$VARIANT" --panels >/dev/null 2>&1 \
  || echo "note: --panels verify needs a frozen roster; it runs again after freeze"

CPUS=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)
ROSTER=$("$PY" -B -c 'import sys;sys.path.insert(0,sys.argv[1]);import fable_operator_reliability as R;print(len(R.parse_seeds(sys.argv[2])))' "$HERE/scripts" "$SEEDS")
PARALLEL=${PARALLEL:-$CPUS}
if [ "$PARALLEL" -gt "$ROSTER" ]; then PARALLEL=$ROSTER; fi
echo "variant=$VARIANT seeds=$SEEDS roster=$ROSTER cpus=$CPUS parallel=$PARALLEL"

OUT="$HERE/artifacts/fable-operator-reliability-$VARIANT-20260920"
rm -f "$HERE/DONE" "$HERE/FAILED"
"$PY" -B "$REL" freeze --repo "$HERE" --variant "$VARIANT" --seeds "$SEEDS"
"$PY" -B "$REL" verify --repo "$HERE" --variant "$VARIANT" --panels
set +e
"$PY" -B "$REL" wave --repo "$HERE" --variant "$VARIANT" --seeds "$SEEDS" \
      --parallel "$PARALLEL" --name "$NAME"
WAVE=$?
set -e
"$PY" -B "$REL" summary --repo "$HERE" --variant "$VARIANT" | tee "$OUT/summary.txt"
"$PY" -B "$REL" summary --repo "$HERE" --variant "$VARIANT" --json > "$OUT/summary.json"
date -u +%Y-%m-%dT%H:%M:%SZ > "$HERE/DONE"
echo "wave exit $WAVE" >> "$HERE/DONE"
if [ "$WAVE" -ne 0 ]; then echo "$WAVE" > "$HERE/FAILED"; fi
echo "DONE written; wave exit $WAVE (non-zero only means >=1 seed did not complete)"
