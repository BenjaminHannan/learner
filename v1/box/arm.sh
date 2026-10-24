#!/bin/bash
# One arm on one box (run by the rent wrapper). Env from the wrapper: ROOT J PY DPH BOX_START RUN_END. Arm-specific env set by the pack's
# ARM.env (ARM=floor|full, STEPS, CAP). Resume (rule A5): if resume.json lists checkpoint files (url + sha256), they are fetched into
# the arm's wake-ckpt / creative dirs first and the runner continues from them.
set -u
cd "$ROOT" || exit 1
. "$ROOT/ARM.env"                      # ARM, STEPS, CAP
export PYTHONPATH="$ROOT" PYTHONHASHSEED=0
C="$J/checks"; O="$ROOT/out/$ARM"; mkdir -p "$C" "$O"
say() { echo "=== $* $(date -u +%FT%TZ)"; }
CORES=$(nproc); W=$(( CORES < 16 ? CORES : 16 ))
say "STEP data (train 380 + dev 20 shards + validation; the sealed test split is NOT built here), workers $W"
$PY -m v1.box_build "$J/data/v1village" --train-shards 380 --dev-shards 20 --workers "$W" > "$C/box_build.out" 2>&1 || { tail -5 "$C/box_build.out"; exit 1; }
tail -1 "$C/box_build.out"
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
if os.path.exists("resume.json"):                      # A5: continue from checkpoints pulled off a dead box
    for f in json.load(open("resume.json")):
        d = urllib.request.urlopen(f["url"], timeout=300).read()
        assert hashlib.sha256(d).hexdigest() == f["sha256"], f["path"]
        p = os.path.join(os.environ["ROOT"], "out", os.environ["ARM"], f["path"])
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(d)
        print("resume file", f["path"], len(d))
print("setup ok")
PYEOF
XARGS=()                                  # optional (ARM.env EXTRA_CMD / DETECTOR_PATTERNS): extra D training shards, v1/extra.py
if [ -n "${EXTRA_CMD:-}" ]; then
  mkdir -p "$J/extra"
  say "STEP extra shards: $EXTRA_CMD"
  ( cd "$ROOT" && bash -c "$EXTRA_CMD" ) > "$C/extra_cmd.out" 2>&1 || { tail -20 "$C/extra_cmd.out"; exit 1; }
  tail -3 "$C/extra_cmd.out"
  for d in $(ls -d "$J"/extra/*/ 2>/dev/null | sort); do XARGS+=(--extra-train "${d%/}"); done
  [ ${#XARGS[@]} = 0 ] && { echo "EXTRA_CMD produced no $J/extra/<subdir>/"; exit 1; }
fi
[ -n "${DETECTOR_PATTERNS:-}" ] && XARGS+=(--detector-patterns "$ROOT/$DETECTOR_PATTERNS")
echo "extra args: ${XARGS[*]:-none}"
say "STEP arm $ARM steps $STEPS at \$$DPH/h, cap \$$CAP"
$PY -m v1.run --arm "$ARM" --root "$J/data/v1village" --out "$O" --b2 "$J/B2_s200.pt" --skills "$J/skills" --steps "$STEPS" \
  --price-per-hour "$DPH" --spend-cap "$CAP" --workers "$W" "${XARGS[@]}" 2>&1 | tee -a "$C/arm_$ARM.out"
RC=${PIPESTATUS[0]}
echo "arm $ARM rc=$RC"
[ -f "$O/final_dev.json" ] && head -c 3000 "$O/final_dev.json"
[ "$RC" = 0 ] || [ "$RC" = 3 ] || exit "$RC"        # 3 = an abort rule fired and the last checkpoint was judged (a result, not a crash)
exit 0
