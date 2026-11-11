#!/bin/bash
# Word-problem experiment on one Vast box (run by the rent wrapper's job body; design/wordprob/PREREG.md).
# Env from the wrapper: ROOT J PY DPH BOX_START RUN_END. WP.env (written by `rent.py pack --kind wordprob`) sets STEPS, CAP,
# and optionally DATA_URL + DATA_SHA (a tar.xz of the data dir, when the data was too big to ship inside the args).
# Runs BOTH arms back to back (answer, then steps), prints each final.json between markers, writes out/DONE.
set -u
cd "$ROOT" || exit 1
. "$ROOT/WP.env"                       # STEPS, CAP, DATA_URL, DATA_SHA
DATA_URL=${DATA_URL:-}; DATA_SHA=${DATA_SHA:-}; export DATA_URL DATA_SHA ROOT
say() { echo "=== $* $(date -u +%FT%TZ)"; }
D="$ROOT/data/wordprob-v1"; O="$ROOT/out"; mkdir -p "$D" "$O"
export PYTHONPATH="$ROOT" PYTHONHASHSEED=0 PYTHONUNBUFFERED=1
if [ -n "${DATA_URL:-}" ]; then
  say "STEP fetch data $DATA_URL"
  $PY - <<'PYEOF' || { echo "data fetch failed"; exit 1; }
import hashlib, os, tarfile, urllib.request
d = urllib.request.urlopen(os.environ["DATA_URL"], timeout=600).read()
assert hashlib.sha256(d).hexdigest() == os.environ["DATA_SHA"], "data sha256 mismatch"
open("/tmp/wp-data.tar.xz", "wb").write(d)
tarfile.open("/tmp/wp-data.tar.xz", "r:xz").extractall(os.path.join(os.environ["ROOT"], "data/wordprob-v1"))
print("data fetched", len(d))
PYEOF
fi
# data may sit in a subfolder after extraction
[ -f "$D/train.jsonl" ] || { F=$(find "$D" -name train.jsonl | head -1); [ -n "$F" ] && D=$(dirname "$F"); }
for f in train dev heldout_template heldout_structure; do [ -f "$D/$f.jsonl" ] || { echo "missing $D/$f.jsonl"; exit 1; }; done
[ -f "$D/MANIFEST.json" ] && { say "MANIFEST sha256"; sha256sum "$D/MANIFEST.json"; }
wc -l "$D"/*.jsonl

RC=0
for ARM in ${WP_ARMS:-answer steps}; do
  say "STEP arm $ARM steps $STEPS at \$$DPH/h, cap \$$CAP"
  if [ "$ARM" = smol ] || [ "$ARM" = smolrand ]; then
    $PY -m pip install -q transformers==4.46.3 accelerate 2>&1 | tail -2
    RI=""; [ "$ARM" = smolrand ] && RI="--random-init"
    $PY "$ROOT/scripts/wordprob/train_smol.py" --data "$D" --out "$O/$ARM" --device "${WP_DEVICE:-cuda}" $RI ${WP_EXTRA:-} 2>&1 | tee -a "$J/checks/arm_$ARM.out"
  else
    $PY "$ROOT/scripts/wordprob/train_wp.py" --data "$D" --arm "$ARM" --out "$O/$ARM" --steps "$STEPS" --device "${WP_DEVICE:-cuda}" ${WP_EXTRA:-} 2>&1 | tee -a "$J/checks/arm_$ARM.out"
  fi
  R=${PIPESTATUS[0]}
  echo "arm $ARM rc=$R"
  [ "$R" = 0 ] || RC=$R
done

for ARM in ${WP_ARMS:-answer steps}; do
  echo "=====BEGIN final.json $ARM====="
  cat "$O/$ARM/final.json" 2>/dev/null || echo "(missing)"
  echo
  echo "=====END final.json $ARM====="
done
echo "DONE rc=$RC $(date -u +%FT%TZ)" > "$O/DONE"
say "WORDPROB DONE rc=$RC"
exit "$RC"
