#!/bin/bash
# One D-only training arm on one box (run by the rent wrapper; kind dgen). Env from the wrapper: ROOT J PY DPH BOX_START RUN_END.
# From the pack's ARM.env: ARM (output name), STEPS, SEED, CAP, WEIGHT_DECAY ('' = default), EXTRA_CMD ('' = none).
# Steps: build the village data (train 380 + dev 20 shards + validation; the sealed test split is NEVER built) -> optional EXTRA_CMD
# writes extra training shards into $J/extra/<subdir>/ -> python -m generalize.dtrain_only (resumes from out/$ARM/wake-ckpt).
# Outputs live in $ROOT/out/$ARM: final.json, D-final.pt (+ dev_evals.jsonl, wake-ckpt/); the wrapper's finish() exports them.
set -u
cd "$ROOT" || exit 1
. "$ROOT/ARM.env"
export PYTHONPATH="$ROOT" PYTHONHASHSEED=0
C="$J/checks"; O="$ROOT/out/$ARM"; mkdir -p "$C" "$O" "$J/extra"
say() { echo "=== $* $(date -u +%FT%TZ)"; }
CORES=$(nproc); W=$(( CORES < 16 ? CORES : 16 ))
say "STEP data (train 380 + dev 20 shards + validation; the sealed test split is NOT built here), workers $W"
$PY -m v1.box_build "$J/data/v1village" --train-shards 380 --dev-shards 20 --workers "$W" > "$C/box_build.out" 2>&1 || { tail -5 "$C/box_build.out"; exit 1; }
tail -1 "$C/box_build.out"
if [ -d "$J/data/v1village/test" ]; then echo "SEALED test dir exists in the data root"; exit 1; fi
if [ -n "${EXTRA_CMD:-}" ]; then
  say "STEP extra shards: $EXTRA_CMD"
  ( cd "$ROOT" && bash -c "$EXTRA_CMD" ) > "$C/extra_cmd.out" 2>&1 || { tail -20 "$C/extra_cmd.out"; exit 1; }
  tail -3 "$C/extra_cmd.out"
fi
EXTRA_ARGS=()
for d in $(ls -d "$J"/extra/*/ 2>/dev/null | sort); do EXTRA_ARGS+=(--extra-train "${d%/}"); done
echo "extra dirs: ${EXTRA_ARGS[*]:-none}"
[ -n "${EXTRA_CMD:-}" ] && [ ${#EXTRA_ARGS[@]} = 0 ] && { echo "EXTRA_CMD produced no $J/extra/<subdir>/"; exit 1; }
WD=(); [ -n "${WEIGHT_DECAY:-}" ] && WD=(--weight-decay "$WEIGHT_DECAY")
# spend guard: what the box has cost so far (setup, data, extras) comes off the cap; 0.15 USD is kept back for export and pull
LEFT=$(awk -v cap="$CAP" -v dph="$DPH" -v now="$(date +%s)" -v t0="$BOX_START" 'BEGIN{l=cap-(now-t0)/3600*dph-0.15; printf "%.3f", (l>0.05?l:0.05)}')
say "STEP arm $ARM steps $STEPS seed $SEED at \$$DPH/h, cap \$$CAP (training guard \$$LEFT)"
$PY -m generalize.dtrain_only --root "$J/data/v1village" --out "$O" --steps "$STEPS" --seed "$SEED" --workers "$W" \
  --price-per-hour "$DPH" --spend-cap "$LEFT" --stop-at-epoch "$((RUN_END - 600))" "${WD[@]}" "${EXTRA_ARGS[@]}" 2>&1 | tee -a "$C/arm_$ARM.out"
RC=${PIPESTATUS[0]}
echo "arm $ARM rc=$RC"
[ -f "$O/final.json" ] && head -c 3000 "$O/final.json"
[ -f "$O/D-final.pt" ] || { echo "NO D-final.pt"; exit 1; }
[ "$RC" = 0 ] || [ "$RC" = 3 ] || exit "$RC"        # 3 = the spend guard / deadline / NaN fired and the last state was judged
exit 0
