#!/bin/bash
# opcpu jobs 4: handoff/queue/pond-{a,b,c,z}-dev.md (one arm per call: job-pond.sh a|b|c|z), science steps unchanged (see DEVIATIONS.md).
# The four queue files differ only in the arm letter and the lambda in their text (0.001, 0.004, 0.016, 0.0): the plug-in claude_dir_pond_<arm> holds the lambda.
set -o pipefail
. "$(dirname "$0")/jlib.sh"
AR=${1:?arm a|b|c|z}; case "$AR" in a|b|c|z) ;; *) echo "bad arm $AR"; exit 2;; esac
G=$OPC_OUT/pond-$AR-dev; W=$HOME/premonition-pond-$AR; A=artifacts/claude-dir-pond-20260928
SRC=${POND_SRC:-$OPC_IN/artifacts/claude-fewex-20260927/runs}
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$G"
echo "start $(date -u '+%F %T') UTC"; uptime; df -h "$HOME" | tail -1
FREE=$(freegb); [ "${FREE:-0}" -ge 3 ] || { echo "ABORT: under 3 GB free"; exit 4; }
[ -f "$OPC_R/$A/SEAL-code.sha256.txt" ] || { echo "WAITING: the pinned tree has no $A/SEAL-code.sha256.txt"; exit 5; }
grep -q '"verdict": "PASS"' "$OPC_R/artifacts/claude-fewex-20260927/EQ-DEV-GATE.json" || { echo "WAITING: baseline ruler gate is not PASS"; exit 5; }
unpack "$W" scripts artifacts/claude-fewex-20260927 $A || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
sha256sum -c $A/SEAL-code.sha256.txt > $A/seal-check-$AR.log 2>&1 || { cat $A/seal-check-$AR.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check-$AR.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
for S in 0 1; do
  [ -f "$SRC/qual-loop-s$S/source.pt" ] && [ -f "$SRC/qual-loop-s$S/source.json" ] || { echo "MISSING-SOURCE: $SRC/qual-loop-s$S"; exit 6; }
  want=$(awk -v f="artifacts/claude-fewex-20260927/runs/qual-loop-s$S/source.json" '$2==f {print $1}' artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt)
  have=$(sha256sum "$SRC/qual-loop-s$S/source.json" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "SOURCE-JSON-MISMATCH seed $S (sealed '$want', box '$have')"; exit 6; }
  echo "seed $S: qualified source.json matches its sealed sha256; source.pt sha256 $(sha256sum "$SRC/qual-loop-s$S/source.pt" | awk '{print $1}')"
done
$PY scripts/claude_dir_pond_marks.py selftest > $A/SELFTEST-marks-mac-$AR.log 2>&1; cat $A/SELFTEST-marks-mac-$AR.log
grep -q '"selftest": "ok"' $A/SELFTEST-marks-mac-$AR.log || { echo "STOP: marks selftest failed"; exit 7; }
$PY scripts/claude_dir_pond_selftest.py > $A/SELFTEST-plugin-mac-$AR.log 2>&1; cat $A/SELFTEST-plugin-mac-$AR.log
grep -q '"selftest": "ok"' $A/SELFTEST-plugin-mac-$AR.log || { echo "STOP: plug-in selftest failed"; exit 7; }
mkdir -p $A/eq-runs
for S in 0 1; do
  O=$A/eq-runs/pond-$AR-pre-s$S
  [ -f $O/adapt.json ] && { echo "seed $S: adapt.json already exists; not re-running"; continue; }
  [ -d $O ] && { echo "PARTIAL: $O exists without adapt.json (the harness has no resume); delete that folder and start again"; exit 7; }
  nohup timeout -s ALRM 17400 $PY scripts/claude_fewex_eq_bench.py adapt --plugin claude_dir_pond_$AR --arm loop --seed $S --init pre --source "$SRC/qual-loop-s$S" --out $O --threads 1 > $A/eq-runs/pond-$AR-pre-s$S.log 2>&1 &
  echo "seed $S pid $! started $(date -u '+%F %T') UTC"
done
wait
FAILED=0
for S in 0 1; do echo "== seed $S"; tail -2 $A/eq-runs/pond-$AR-pre-s$S.log; ls -l $A/eq-runs/pond-$AR-pre-s$S/adapt.json || FAILED=1; done
mkdir -p "$G/$A/eq-runs"; cp $A/eq-runs/pond-$AR-*.log "$G/$A/eq-runs/" 2>/dev/null; cp $A/SELFTEST-marks-mac-$AR.log $A/SELFTEST-plugin-mac-$AR.log $A/seal-check-$AR.log "$G/$A/"
[ "$FAILED" = 0 ] || { echo "STOP: a run has no adapt.json; report the first traceback in its log verbatim"; exit 8; }
$PY scripts/claude_dir_pond_marks.py judge --arms $AR --out $A/JUDGE-dev-$AR.json > $A/JUDGE-dev-$AR.log 2>&1 || { tail -20 $A/JUDGE-dev-$AR.log; cp $A/JUDGE-dev-$AR.log "$G/$A/"; echo "STOP: judge failed"; exit 9; }
ARM=$AR $PY - <<'PYEOF'
import json, os
arm = os.environ["ARM"]
d = json.load(open("artifacts/claude-dir-pond-20260928/JUDGE-dev-%s.json" % arm))
a = d["arms"][arm]
print("ARM " + arm + " lambda", a["lambda"], "WORD", a["word"], "| overall (one arm only, not the sweep verdict)", d["overall"])
for s in ("0", "1"):
    if "seeds" not in a:
        break
    m = a["seeds"][s]
    print("seed", s, "S1 rungs", m["s1_rungs_passing"], "of 5 (need 4)", "S2 rungs", m["s2_rungs_passing"], "of 5 (need 4)", "F_eq learned %.2f fixed16 %.2f | F_few learned %.2f fixed16 %.2f" % (m["F"]["F_eq"]["learned"], m["F"]["F_eq"]["fixed"], m["F"]["F_few"]["learned"], m["F"]["F_few"]["fixed"]))
    for k, r in m["rungs"].items():
        print("  k", k, "right", r["right"], "fixed16", r["fixed_right"], "cap_hits", r["cap_hits"], "mean_rounds", r["mean_rounds"], "S1", r["S1"], "S2", r["S2"])
if "rows" in a:
    print("rows", {r: a["rows"][r] for r in ("A1", "A2", "P", "body_reading")})
PYEOF
sha256sum $A/eq-runs/pond-$AR-pre-s?/adapt.json $A/JUDGE-dev-$AR.json > $A/SHA256-pond-$AR-dev.txt
for S in 0 1; do mkdir -p "$G/$A/eq-runs/pond-$AR-pre-s$S"; cp $A/eq-runs/pond-$AR-pre-s$S/adapt.json "$G/$A/eq-runs/pond-$AR-pre-s$S/"; done
cp $A/JUDGE-dev-$AR.json $A/JUDGE-dev-$AR.log $A/SHA256-pond-$AR-dev.txt "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
