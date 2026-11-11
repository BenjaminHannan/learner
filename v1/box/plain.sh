#!/bin/bash
# The plain-transformer baseline on one box (run by the rent wrapper; design/v1/plain-baseline/PREREG.md). Env from the wrapper:
# ROOT J PY DPH BOX_START RUN_END. ARM.env (written by `rent.py pack --kind plain`) sets ARM=plain, STEPS, CAP.
# No skills set and no B2 parent (the plain model uses neither). The sealed test split is not built here.
# Resume (rule A5): if resume.json lists checkpoint files (url + sha256), they are fetched into out/plain first.
set -u
cd "$ROOT" || exit 1
. "$ROOT/ARM.env"                      # ARM=plain, STEPS, CAP
export PYTHONPATH="$ROOT" PYTHONHASHSEED=0
C="$J/checks"; O="$ROOT/out/$ARM"; mkdir -p "$C" "$O"
say() { echo "=== $* $(date -u +%FT%TZ)"; }
CORES=$(nproc); W=$(( CORES < 16 ? CORES : 16 ))
say "STEP data (train 380 + dev 20 shards + validation; the sealed test split is NOT built here), workers $W"
$PY -m v1.box_build "$J/data/v1village" --train-shards 380 --dev-shards 20 --workers "$W" > "$C/box_build.out" 2>&1 || { tail -5 "$C/box_build.out"; exit 1; }
tail -1 "$C/box_build.out"
if [ -f resume.json ]; then
$PY - <<'PYEOF' || exit 1
import hashlib, json, os, urllib.request
for f in json.load(open("resume.json")):
    d = urllib.request.urlopen(f["url"], timeout=300).read()
    assert hashlib.sha256(d).hexdigest() == f["sha256"], f["path"]
    p = os.path.join(os.environ["ROOT"], "out", os.environ["ARM"], f["path"])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(d)
    print("resume file", f["path"], len(d))
PYEOF
fi
say "STEP plain baseline steps $STEPS at \$$DPH/h, cap \$$CAP"
$PY -m v1.plain_baseline --root "$J/data/v1village" --out "$O" --steps "$STEPS" --workers "$W" 2>&1 | tee -a "$C/arm_$ARM.out"
RC=${PIPESTATUS[0]}
echo "arm $ARM rc=$RC"
[ -f "$O/final_dev.json" ] && head -c 3000 "$O/final_dev.json"
exit "$RC"
