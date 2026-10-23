#!/bin/bash
# Round 2 (Occam dreams) of the multi-step creative experiment (design/v1/multistep/PREREG.md "Round 2"; run by the rent wrapper). Env as multistep.sh. Arms: base occam5 occam5_strict oracle; the 128-core box generates the Occam dreams (find_reference) in parallel.
# No village data, no D, no bridge: skills set + hash-checked B2_s200, then creative.multistep (2 seeds x 6 arms, K processes at a time on the one GPU).
# Resumable: a re-run skips finished arms (put the out dir back first). The sealed test split is never read.
set -u
cd "$ROOT" || exit 1
export PYTHONPATH="$ROOT" PYTHONHASHSEED=0
C="$J/checks"; O="$ROOT/out/multistep"; mkdir -p "$C" "$O"
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
say "STEP multistep2 ROUND 2 Occam (2 seeds, 4 arms, side by side) at \$$DPH/h"
for S in 0 1; do   # the two seeds run side by side (each its own driver, 6 arms at a time); the last call only aggregates (every arm is skipped as finished)
  $PY -m creative.multistep --b2 "$J/B2_s200.pt" --skills "$J/skills" --out "$O" --cache-dir "$J/dreamcache" --device cuda --round 2 --arms base occam5 occam5_strict oracle --seeds $S --parallel 4 > "$C/seed$S.out" 2>&1 &
done
wait
tail -5 "$C/seed0.out" "$C/seed1.out"
$PY -m creative.multistep --b2 "$J/B2_s200.pt" --skills "$J/skills" --out "$O" --cache-dir "$J/dreamcache" --device cuda --round 2 --arms base occam5 occam5_strict oracle --seeds 0 1 --parallel 4 2>&1 | tee -a "$C/arm_multistep.out"
RC=${PIPESTATUS[0]}
echo "multistep2 rc=$RC"
[ -f "$O/results.json" ] && head -c 20000 "$O/results.json"
exit "$RC"
