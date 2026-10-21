#!/bin/bash
# Gate S GPU job body (run by the rent wrapper on the box; ROOT = the unpacked tree, J = job dir, PY = python).
# Order: data subset (hash-checked) -> skills set (hash-checked) -> B2 parent (hash-checked) -> preflight + 5 steps -> overfit ->
# components (S2/Muon/bridge/G1 KL/sleep) -> 2% of steps per arm (real plan) -> compressed full-curriculum run per arm -> resume check.
set -u
cd "$ROOT" || exit 1
export PYTHONPATH="$ROOT" PYTHONHASHSEED=0 CUBLAS_WORKSPACE_CONFIG=:4096:8
C="$J/checks"; O="$ROOT/out"; mkdir -p "$C" "$O"
say() { echo "=== $* $(date -u +%FT%TZ)"; }
fail() { say "V1G-FAIL $*"; return 1; }
CORES=$(nproc); W=$(( CORES < 8 ? CORES : 8 ))
say "STEP data subset (workers $W)"
$PY -m v1.box_build "$J/data/v1village" --train-shards 48 --dev-shards 4 --workers "$W" > "$C/box_build.out" 2>&1 || { tail -5 "$C/box_build.out"; fail "box_build"; exit 1; }
tail -1 "$C/box_build.out"
say "STEP skills set"
$PY -m skills_curriculum.build --out "$J/skills" --train 200000 --dev-per-cell 40 --seed 1 > "$C/skills.out" 2>&1 || { tail -3 "$C/skills.out"; fail "skills build"; exit 1; }
$PY - <<'PYEOF' > "$C/skills_check.out" 2>&1 || { cat "$C/skills_check.out"; fail "skills hashes"; exit 1; }
import json, os
ref = json.load(open("skills_curriculum/FULL-BUILD-MANIFEST-200k-seed1.json"))["files_sha256"]
have = json.load(open(os.environ["J"] + "/skills/manifest.json"))["files_sha256"]
assert ref == have, "skills build differs from the committed manifest"
print("skills hashes match", len(ref))
PYEOF
cat "$C/skills_check.out"
say "STEP B2 parent"
$PY - <<'PYEOF' > "$C/b2_fetch.out" 2>&1 || { cat "$C/b2_fetch.out"; fail "B2 fetch"; exit 1; }
import hashlib, os, urllib.request
url = "https://raw.githubusercontent.com/BenjaminHannan/learner/claude/b2-confirm-checkpoints/custom_io/checkpoints/33-b2-confirm/B2_s200/checkpoint.pt"
data = urllib.request.urlopen(url, timeout=120).read()
h = hashlib.sha256(data).hexdigest()
assert h == "94057436d98a485cb4ed0bc750244c2d86a2c744d249106276b15effe94b9d3a", h
open(os.environ["J"] + "/B2_s200.pt", "wb").write(data)
print("B2_s200 ok", len(data))
PYEOF
cat "$C/b2_fetch.out"
B2="$J/B2_s200.pt"; ROOTD="$J/data/v1village"; SK="$J/skills"
say "STEP preflight (pinned versions, guard from card, 5 FULL-arm steps)"
V1_ROOT="$ROOTD" $PY -m v1.preflight --pins v1/PINS.json --device cuda --commit-file "$ROOT/COMMIT" --five-steps v1.gate_s:five_steps > "$C/preflight.json" 2> "$C/preflight.err"; echo "preflight rc=$?"; cat "$C/preflight.json" | head -60; tail -3 "$C/preflight.err"
say "STEP overfit"
$PY -m v1.gate_s overfit --root "$ROOTD" --b2 "$B2" --skills "$SK" --out "$O/gs" --device cuda --steps 300 > "$C/overfit.out" 2>&1; echo "overfit rc=$?"; tail -3 "$C/overfit.out"
say "STEP components"
$PY -m v1.gate_s components --root "$ROOTD" --b2 "$B2" --skills "$SK" --out "$O/gs" --device cuda --cap 40 --diary 512 --pool 64 --devn 64 > "$C/components.out" 2>&1; echo "components rc=$?"; tail -3 "$C/components.out"
for ARM in floor full; do
  say "STEP 2% of steps, real plan, arm $ARM"
  $PY -m v1.run --arm $ARM --root "$ROOTD" --out "$O/two_pct_$ARM" --b2 "$B2" --skills "$SK" --steps 12000 --stop-after 240 --no-sleep --eval-visits 256 --ckpt-every 120 --eval-every 120 --workers "$W" > "$C/two_pct_$ARM.out" 2>&1; echo "2pct $ARM rc=$?"; grep -E "step 2(00|40)|DEV|ABORT|Error" "$C/two_pct_$ARM.out" | tail -4
  say "STEP compressed full curriculum, arm $ARM"
  $PY -m v1.run --arm $ARM --root "$ROOTD" --out "$O/compressed_$ARM" --b2 "$B2" --skills "$SK" --steps 400 --no-sleep --eval-visits 256 --ckpt-every 100 --eval-every 100 --workers "$W" > "$C/compressed_$ARM.out" 2>&1; echo "compressed $ARM rc=$?"; grep -E "DEV|ABORT|Error" "$C/compressed_$ARM.out" | tail -5
done
say "STEP resume check"
$PY -m v1.run --arm full --root "$ROOTD" --out "$O/res_A" --b2 "$B2" --skills "$SK" --steps 40 --max-tokens 20000 --no-sleep --eval-visits 32 --ckpt-every 10 --eval-every 1000 --workers "$W" > "$C/res_A.out" 2>&1
$PY -m v1.run --arm full --root "$ROOTD" --out "$O/res_B" --b2 "$B2" --skills "$SK" --steps 40 --max-tokens 20000 --no-sleep --eval-visits 32 --ckpt-every 10 --eval-every 1000 --stop-after 25 --workers "$W" > "$C/res_B1.out" 2>&1
$PY -m v1.run --arm full --root "$ROOTD" --out "$O/res_B" --b2 "$B2" --skills "$SK" --steps 40 --max-tokens 20000 --no-sleep --eval-visits 32 --ckpt-every 10 --eval-every 1000 --workers "$W" > "$C/res_B2.out" 2>&1
$PY -m v1.gate_s resume_compare --a "$O/res_A" --b "$O/res_B" --out "$O/gs" > "$C/resume.out" 2>&1; tail -3 "$C/resume.out"
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader > "$C/gpu_end.txt" 2>&1
say "STEPS DONE"
exit 0
