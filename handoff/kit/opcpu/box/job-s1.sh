#!/bin/bash
# opcpu jobs 6 and 7: handoff/queue/s1-loop-mac.md and s1-plain-mac.md (one arm per call: job-s1.sh loop|plain), science steps unchanged
# (see DEVIATIONS.md). The two queue files differ only in loop/plain in their text and file names.
set -o pipefail
. "$(dirname "$0")/jlib.sh"
AR=${1:?arm loop|plain}; case "$AR" in loop|plain) ;; *) echo "bad arm $AR"; exit 2;; esac
G=$OPC_OUT/s1-$AR; W=$HOME/premonition-s1-$AR; A=artifacts/claude-s1-d4-20260929
SRC=${S1_SRC:-$OPC_IN/artifacts/claude-fewex-20260927/runs}
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
  [ -f "$SRC/qual-$AR-s$S/source.pt" ] && [ -f "$SRC/qual-$AR-s$S/source.json" ] || { echo "MISSING-SOURCE: $SRC/qual-$AR-s$S"; exit 6; }
  want=$(awk -v f="artifacts/claude-fewex-20260927/runs/qual-$AR-s$S/source.json" '$2==f {print $1}' artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt)
  have=$(sha256sum "$SRC/qual-$AR-s$S/source.json" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "SOURCE-JSON-MISMATCH seed $S (sealed '$want', box '$have')"; exit 6; }
  echo "seed $S: qualified source.json matches its sealed sha256; source.pt sha256 $(sha256sum "$SRC/qual-$AR-s$S/source.pt" | awk '{print $1}')"
done
$PY scripts/claude_s1_d4_marks.py selftest > $A/SELFTEST-marks-mac-$AR.log 2>&1; cat $A/SELFTEST-marks-mac-$AR.log
grep -q '"selftest": "ok"' $A/SELFTEST-marks-mac-$AR.log || { echo "STOP: marks selftest failed"; exit 7; }
$PY scripts/claude_s1_d4_selftest.py > $A/SELFTEST-plugin-mac-$AR.log 2>&1; tail -2 $A/SELFTEST-plugin-mac-$AR.log
grep -q '"selftest": "ok", "part_b": "ran"' $A/SELFTEST-plugin-mac-$AR.log || { echo "STOP: plug-in selftest failed (part B must run here)"; exit 7; }
mkdir -p $A/eq-runs
for S in 0 1; do
  O=$A/eq-runs/s1-$AR-pre-s$S
  [ -f $O/adapt.json ] && { echo "seed $S: adapt.json already exists; not re-running"; continue; }
  [ -d $O ] && { echo "PARTIAL: $O exists without adapt.json (the harness has no resume); delete that folder and start again"; exit 7; }
  nohup timeout -s ALRM 17400 $PY scripts/claude_fewex_eq_bench.py adapt --plugin claude_s1_d4 --arm $AR --seed $S --init pre --source "$SRC/qual-$AR-s$S" --out $O --threads 1 > $A/eq-runs/s1-$AR-pre-s$S.log 2>&1 &
  echo "seed $S pid $! started $(date -u '+%F %T') UTC"
done
wait
FAILED=0
for S in 0 1; do echo "== seed $S"; grep d4_views $A/eq-runs/s1-$AR-pre-s$S.log | tail -2; tail -2 $A/eq-runs/s1-$AR-pre-s$S.log; ls -l $A/eq-runs/s1-$AR-pre-s$S/adapt.json || FAILED=1; done
mkdir -p "$G/$A/eq-runs"; cp $A/eq-runs/s1-$AR-*.log "$G/$A/eq-runs/" 2>/dev/null; cp $A/SELFTEST-marks-mac-$AR.log $A/SELFTEST-plugin-mac-$AR.log $A/seal-check-$AR.log "$G/$A/"
[ "$FAILED" = 0 ] || { echo "STOP: a run has no adapt.json; report the first traceback in its log verbatim"; exit 8; }
# report-only 8-view vote (dev panel only, no mark reads it)
for S in 0 1; do
  nohup timeout -s ALRM 7200 $PY scripts/claude_s1_d4_vote.py run --arm $AR --seed $S --dir $A/eq-runs/s1-$AR-pre-s$S --source "$SRC/qual-$AR-s$S" > $A/eq-runs/s1-$AR-vote-s$S.log 2>&1 &
done
wait
for S in 0 1; do echo "== vote seed $S"; tail -3 $A/eq-runs/s1-$AR-vote-s$S.log; done
sha256sum $A/eq-runs/s1-$AR-pre-s?/adapt.json $A/eq-runs/s1-$AR-pre-s?/vote.json > $A/SHA256-s1-$AR-dev.txt 2>/dev/null
for S in 0 1; do mkdir -p "$G/$A/eq-runs/s1-$AR-pre-s$S"; cp $A/eq-runs/s1-$AR-pre-s$S/adapt.json "$G/$A/eq-runs/s1-$AR-pre-s$S/"; cp $A/eq-runs/s1-$AR-pre-s$S/vote.json "$G/$A/eq-runs/s1-$AR-pre-s$S/" 2>/dev/null; done
cp $A/eq-runs/s1-$AR-*.log "$G/$A/eq-runs/"; cp $A/SHA256-s1-$AR-dev.txt "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
