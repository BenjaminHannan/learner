#!/bin/bash
# G1 ablation on one box (design/v1/g1-ablate/PREREG.md; run by the rent wrapper). Env from the wrapper: ROOT J PY DPH BOX_START RUN_END.
# Creative module only: skills set + hash-checked B2_s200, then v1.g1_ablate (seed 1 for the replication run; seed 0 ran 2026-10-24, arms g1_empirical g1_example g1_off, one after the other).
# No village data, no D, no bridge. Resumable: a re-run skips finished stages/arms (put the out dir back first). The sealed test split is never read.
set -u
cd "$ROOT" || exit 1
export PYTHONPATH="$ROOT" PYTHONHASHSEED=0
C="$J/checks"; O="$ROOT/out/g1ablate"; mkdir -p "$C" "$O"
say() { echo "=== $* $(date -u +%FT%TZ)"; }
say "STEP skills set + B2 parent (hash-checked)"
$PY -m skills_curriculum.build --out "$J/skills" --train 200000 --dev-per-cell 40 --seed 1 > "$C/skills.out" 2>&1 || exit 1
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
say "STEP g1 ablation (seed 1, 3 arms in sequence) at \$$DPH/h"
$PY -m v1.g1_ablate --b2 "$J/B2_s200.pt" --skills "$J/skills" --out "$O" --device cuda --seeds 1 2>&1 | tee -a "$C/arm_g1ablate.out"
RC=${PIPESTATUS[0]}
echo "g1ablate rc=$RC"
[ -f "$O/results.json" ] && head -c 20000 "$O/results.json"
exit "$RC"
