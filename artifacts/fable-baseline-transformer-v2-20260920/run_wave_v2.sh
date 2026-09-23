#!/bin/zsh
# Baseline v2 wave launcher -- ONE arm x THREE registered seeds = THREE processes per call.
#
#   usage: run_wave_v2.sh <I0-H0|I0-H1|I1-H0|I1-H1> [updates] [time-cap-seconds]
#
# Registered by artifacts/fable-baseline-transformer-v2-20260920/PREREGISTRATION.md
# (from design/v3/18-baseline-v2-preregistration-draft.md).
#
# Before the FIRST wave, build and freeze the panels:
#
#   PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
#   cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
#   OUT=artifacts/fable-baseline-transformer-v2-20260920
#   PAN=artifacts/fable-dispatcher-v3-20260920/panels
#   $PY -B scripts/fable_baseline_transformer_v2.py panels --kind fit \
#       --out $OUT/fit-panels --exclude $PAN
#   $PY -B scripts/fable_baseline_transformer_v2.py panels --kind confirm \
#       --out $OUT/confirm-panels --exclude $PAN --exclude $OUT/fit-panels
#   shasum -a 256 $OUT/fit-panels/manifest.json $OUT/fit-panels/forbidden-semantics.json \
#                 $OUT/confirm-panels/manifest.json $OUT/confirm-panels/forbidden-semantics.json \
#       >> $OUT/FREEZE.sha256
#
# Then, only when the Mac's registered waves are idle, run the primary arm FIRST:
#   $OUT/run_wave_v2.sh I1-H1
# followed by I0-H1, I1-H0, I0-H0.
#
# Projected: ~15-16 min of training per seed (three run in parallel) plus ~30 s of fit
# scoring per seed, i.e. ~16 min per wave, inside the 25-minute ceiling.
set -u
ROOT=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
cd $ROOT || exit 2
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
OUT=$ROOT/artifacts/fable-baseline-transformer-v2-20260920
PAN=$ROOT/artifacts/fable-dispatcher-v3-20260920/panels
FIT=$OUT/fit-panels
CONFIRM=$OUT/confirm-panels
SEEDS=(1200 1201 1202)
export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1

arm=${1:-}
upd=${2:-6000}
cap=${3:-1200}
case $arm in
  I0-H0|I0-H1|I1-H0|I1-H1) ;;
  *) echo "usage: run_wave_v2.sh <I0-H0|I0-H1|I1-H0|I1-H1> [updates] [time-cap]"; exit 2 ;;
esac
mkdir -p $OUT/logs

# 1. the frozen sources, registration and launcher
shasum -a 256 -c $OUT/FREEZE.sha256 > $OUT/logs/$arm.freezecheck.log 2>&1 \
  || { echo "FREEZE MISMATCH -- see $OUT/logs/$arm.freezecheck.log"; exit 3; }

# 2. the panels must exist AND be covered by the freeze (see the header)
for p in $FIT $CONFIRM; do
  [[ -f $p/manifest.json ]] || { echo "missing panels: $p -- run the 'panels' subcommand"; exit 4; }
done
grep -q 'fit-panels/manifest.json' $OUT/FREEZE.sha256 || {
  echo "FREEZE.sha256 does not cover fit-panels/manifest.json -- append it first"; exit 4; }
grep -q 'confirm-panels/manifest.json' $OUT/FREEZE.sha256 || {
  echo "FREEZE.sha256 does not cover confirm-panels/manifest.json -- append it first"; exit 4; }

# 3. every per-cell hash, the namespaces, the sizes and the disjointness of the two panels
$PY -B -c '
import json, sys
sys.path.insert(0, "scripts")
import fable_baseline_transformer_v2 as B2
fit_manifest, _, fit_signatures = B2.load_fit_panels(sys.argv[1])
con_manifest, _, con_signatures = B2.load_fit_panels(sys.argv[2])
assert fit_manifest["namespace"] == B2.FIT_PANEL_NAMESPACE, "wrong fit namespace"
assert con_manifest["namespace"] == B2.CONFIRM_PANEL_NAMESPACE, "wrong confirmation namespace"
assert fit_manifest["n"] == con_manifest["n"] == B2.FIT_N, "panels are not 512 units per cell"
assert fit_manifest["gate"] == B2.FIT_GATE, "panel gate is not the registered gate"
assert not (fit_signatures & con_signatures), "fit and confirmation panels overlap"
print(json.dumps(dict(fit=len(fit_signatures), confirm=len(con_signatures),
                      gate=fit_manifest["gate"])))
' $FIT $CONFIRM > $OUT/logs/$arm.panelcheck.log 2>&1 \
  || { echo "PANEL CHECK FAILED -- see $OUT/logs/$arm.panelcheck.log"; exit 5; }
cat $OUT/logs/$arm.panelcheck.log

# 4. concurrency guard: the draft requires the Mac's registered waves to be idle
running=$(ps -Ao command | grep -c "[p]ython3.12 -B")
if [[ ${ALLOW_BUSY:-0} != 1 && $running -gt 0 ]]; then
  echo "refusing to launch: $running python3.12 -B process(es) already running"
  echo "(set ALLOW_BUSY=1 only if you have decided those are not registered waves)"
  exit 6
fi

echo "$(date +%H:%M:%S) WAVE $arm START  updates=$upd cap=${cap}s seeds=${SEEDS[*]}"
for s in $SEEDS; do (
  $PY -B scripts/fable_baseline_transformer_v2.py train \
      --arm $arm --seed $s --updates $upd --time-cap $cap \
      --train-namespace astra-baseline-v2-fit \
      --mode steps --positions line \
      --visits 16 --questions-per-world 4 --train-people 6 \
      --width 48 --layers 3 --heads 4 --hidden 208 \
      --lr 1e-3 --lr-final 1e-4 --warmup 100 --clip 1.0 --weight-decay 0.1 \
      --log-every 100 \
      --exclude $PAN --exclude $FIT --exclude $CONFIRM \
      --out $OUT/$arm/seed-$s > $OUT/logs/$arm-seed-$s.train.log 2>&1 \
  && $PY -B scripts/fable_baseline_transformer_v2.py fit \
      --run $OUT/$arm/seed-$s --panels $FIT --block 32 \
      > $OUT/logs/$arm-seed-$s.fit.log 2>&1
  echo "$(date +%H:%M:%S) $arm seed $s rc=$?"
) & done; wait

echo "$(date +%H:%M:%S) WAVE $arm DONE"
$PY -B -c '
import json, pathlib, sys
arm, out = sys.argv[1], sys.argv[2]
for seed in sys.argv[3:]:
    path = pathlib.Path(out) / arm / ("seed-" + seed) / "fit" / "fit.json"
    if not path.exists():
        print(arm, "seed", seed, "-- NO fit.json (see the logs)")
        continue
    report = json.loads(path.read_text())
    gate = report["gate"]
    cells = " ".join("%s=%d/%d" % (cell, gate["cells"][cell]["answers"],
                                   gate["cells"][cell]["strict"])
                     for cell in report["cell_order"])
    print(arm, "seed", seed, "updates", report["updates"],
          "| complete", report["complete"],
          "| one_hop_lookup_gate", gate["one_hop_lookup_gate"],
          "| fit_gate", gate["fit_gate"], "| answers/strict:", cells)
' $arm $OUT $SEEDS
