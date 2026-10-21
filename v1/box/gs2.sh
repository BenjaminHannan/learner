#!/bin/bash
# Gate S GPU job 2: D memory + throughput at the real batch size, the 2% runs, a compressed full-curriculum run per arm, and the resume check.
# (Job 1 showed D at 55,000 tokens/batch peaks at 22.19 GiB reserved on a 24 GB card, over the 0.9 x card guard of 21.16 GiB.)
set -u
cd "$ROOT" || exit 1
export PYTHONPATH="$ROOT" PYTHONHASHSEED=0 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
C="$J/checks"; O="$ROOT/out"; mkdir -p "$C" "$O"
say() { echo "=== $* $(date -u +%FT%TZ)"; }
CORES=$(nproc); W=$(( CORES < 8 ? CORES : 8 ))
say "STEP data subset (workers $W)"
$PY -m v1.box_build "$J/data/v1village" --train-shards 48 --dev-shards 4 --workers "$W" > "$C/box_build.out" 2>&1 || { tail -5 "$C/box_build.out"; exit 1; }
say "STEP skills set + B2"
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
B2="$J/B2_s200.pt"; ROOTD="$J/data/v1village"; SK="$J/skills"
CHOSEN=""
for MT in 55000 40000 32000 24000; do
  OK=1
  for ARM in floor full; do
    say "STEP memory/throughput: arm $ARM max-tokens $MT (40-step compressed curriculum: gold, teacher AND own phases, so the 8-loop memory peak is measured)"
    rm -rf "$O/mt_${ARM}_$MT"
    $PY -m v1.run --arm $ARM --root "$ROOTD" --out "$O/mt_${ARM}_$MT" --b2 "$B2" --skills "$SK" --steps 40 --no-sleep --max-tokens $MT --eval-visits 64 --ckpt-every 1000 --eval-every 1000 --workers "$W" > "$C/mt_${ARM}_$MT.out" 2>&1
    RC=$?; echo "mt $ARM $MT rc=$RC"; [ -f "$O/mt_${ARM}_$MT/wake-done.json" ] && cat "$O/mt_${ARM}_$MT/wake-done.json" | head -c 600; echo
    [ "$RC" = 0 ] || OK=0
  done
  if [ "$OK" = 1 ]; then CHOSEN=$MT; break; fi
done
echo "CHOSEN_MAX_TOKENS=${CHOSEN:-none}" | tee "$C/chosen.txt"
[ -n "$CHOSEN" ] || exit 1
for ARM in floor full; do
  say "STEP compressed full curriculum (300 steps = the ~2% check, all phases), arm $ARM, max-tokens $CHOSEN"
  $PY -m v1.run --arm $ARM --root "$ROOTD" --out "$O/compressed_$ARM" --b2 "$B2" --skills "$SK" --steps 300 --no-sleep --max-tokens $CHOSEN --eval-visits 256 --ckpt-every 100 --eval-every 100 --workers "$W" > "$C/compressed_$ARM.out" 2>&1; echo "compressed $ARM rc=$?"; grep -E "DEV|ABORT" "$C/compressed_$ARM.out" | tail -5 | cut -c1-240; cat "$O/compressed_$ARM/wake-done.json" | head -c 700; echo
done
say "STEP resume check (arm full)"
$PY -m v1.run --arm full --root "$ROOTD" --out "$O/res_B" --b2 "$B2" --skills "$SK" --steps 40 --max-tokens 20000 --no-sleep --eval-visits 32 --ckpt-every 10 --eval-every 1000 --stop-after 25 --workers "$W" > "$C/res_B1.out" 2>&1
$PY -m v1.run --arm full --root "$ROOTD" --out "$O/res_B" --b2 "$B2" --skills "$SK" --steps 40 --max-tokens 20000 --no-sleep --eval-visits 32 --ckpt-every 10 --eval-every 1000 --workers "$W" > "$C/res_B2.out" 2>&1
$PY -m v1.gate_s resume_compare --after 20 --a "$O/res_B" --b "$O/res_B" --out "$O/gs" > "$C/resume.out" 2>&1; tail -12 "$C/resume.out"
say "STEPS DONE"
exit 0
