#!/bin/bash
# Deterministic-GPU resume re-run (coordinator ruling, cap $0.40): same check as gs2's last step with torch deterministic algorithms on.
set -u
cd "$ROOT" || exit 1
export PYTHONPATH="$ROOT" PYTHONHASHSEED=0 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUBLAS_WORKSPACE_CONFIG=:4096:8
C="$J/checks"; O="$ROOT/out"; mkdir -p "$C" "$O"
say() { echo "=== $* $(date -u +%FT%TZ)"; }
CORES=$(nproc); W=$(( CORES < 8 ? CORES : 8 ))
say "STEP data subset (workers $W)"
$PY -m v1.box_build "$J/data/v1village" --train-shards 12 --dev-shards 1 --workers "$W" > "$C/box_build.out" 2>&1 || { tail -5 "$C/box_build.out"; exit 1; }
$PY -m skills_curriculum.build --out "$J/skills" --train 200000 --dev-per-cell 40 --seed 1 > "$C/skills.out" 2>&1 || exit 1
$PY - <<'PYEOF' || exit 1
import hashlib, json, os, urllib.request
ref = json.load(open("skills_curriculum/FULL-BUILD-MANIFEST-200k-seed1.json"))["files_sha256"]
assert ref == json.load(open(os.environ["J"] + "/skills/manifest.json"))["files_sha256"], "skills hashes differ"
data = urllib.request.urlopen("https://raw.githubusercontent.com/BenjaminHannan/learner/claude/b2-confirm-checkpoints/custom_io/checkpoints/33-b2-confirm/B2_s200/checkpoint.pt", timeout=120).read()
assert hashlib.sha256(data).hexdigest() == "94057436d98a485cb4ed0bc750244c2d86a2c744d249106276b15effe94b9d3a"
open(os.environ["J"] + "/B2_s200.pt", "wb").write(data)
PYEOF
B2="$J/B2_s200.pt"; ROOTD="$J/data/v1village"; SK="$J/skills"
for ARM in full floor; do
  say "STEP deterministic resume check, arm $ARM"
  rm -rf "$O/res_$ARM"
  $PY -m v1.run --deterministic --arm $ARM --root "$ROOTD" --out "$O/res_$ARM" --b2 "$B2" --skills "$SK" --steps 40 --max-tokens 20000 --no-sleep --eval-visits 32 --ckpt-every 10 --eval-every 1000 --stop-after 25 --workers "$W" > "$C/res_${ARM}_1.out" 2>&1
  $PY -m v1.run --deterministic --arm $ARM --root "$ROOTD" --out "$O/res_$ARM" --b2 "$B2" --skills "$SK" --steps 40 --max-tokens 20000 --no-sleep --eval-visits 32 --ckpt-every 10 --eval-every 1000 --workers "$W" > "$C/res_${ARM}_2.out" 2>&1
  $PY -m v1.gate_s resume_compare --after 20 --a "$O/res_$ARM" --b "$O/res_$ARM" --out "$O/gs_$ARM" > "$C/resume_$ARM.out" 2>&1; head -12 "$C/resume_$ARM.out"
  grep -c "does not have a deterministic" "$C/res_${ARM}_2.out"
done
say "STEPS DONE"
exit 0
