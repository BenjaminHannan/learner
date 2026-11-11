#!/bin/bash
# One arm of the creative-only dream2 A/B on one box (design/v1/dream2/PREREG.md). Env from the wrapper: ROOT J PY DPH BOX_START RUN_END.
# ARM.env (from `rent.py pack --kind creative --arm control|treat`) sets ARM, CAP. No village data; skills set + B2 parent hash-checked as in arm.sh.
set -u
cd "$ROOT" || exit 1
. "$ROOT/ARM.env"                      # ARM=control|treat, STEPS (unused), CAP
export PYTHONPATH="$ROOT" PYTHONHASHSEED=0
C="$J/checks"; O="$ROOT/out/$ARM"; mkdir -p "$C" "$O"
say() { echo "=== $* $(date -u +%FT%TZ)"; }
say "STEP skills set + B2 parent (hash-checked)"
$PY -m skills_curriculum.build --out "$J/skills" --train 200000 --dev-per-cell 40 --seed 1 > "$C/skills.out" 2>&1 || { tail -5 "$C/skills.out"; exit 1; }
$PY - <<'PYEOF' || exit 1
import hashlib, json, os, urllib.request
ref = json.load(open("skills_curriculum/FULL-BUILD-MANIFEST-200k-seed1.json"))["files_sha256"]
assert ref == json.load(open(os.environ["J"] + "/skills/manifest.json"))["files_sha256"], "skills hashes differ"
url = "https://raw.githubusercontent.com/BenjaminHannan/learner/claude/b2-confirm-checkpoints/custom_io/checkpoints/33-b2-confirm/B2_s200/checkpoint.pt"
data = urllib.request.urlopen(url, timeout=120).read()
assert hashlib.sha256(data).hexdigest() == "94057436d98a485cb4ed0bc750244c2d86a2c744d249106276b15effe94b9d3a"
open(os.environ["J"] + "/B2_s200.pt", "wb").write(data)
print("setup ok")
PYEOF
say "STEP creative A/B arm $ARM at \$$DPH/h, cap \$$CAP"
$PY -m v1.creative_ab --arm "$ARM" --b2 "$J/B2_s200.pt" --skills "$J/skills" --out "$O" 2>&1 | tee -a "$C/arm_$ARM.out"
RC=${PIPESTATUS[0]}
echo "arm $ARM rc=$RC"
[ -f "$O/final.json" ] && head -c 3000 "$O/final.json"
exit "$RC"
