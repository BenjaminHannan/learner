#!/bin/bash
# opcpu job 5: handoff/queue/pond-doubt.md, science steps unchanged (see DEVIATIONS.md). Started by drive.sh after all four pond arms ended.
# The arms ran in private folders ($HOME/premonition-pond-<arm>); this job's own work folder $HOME/premonition-pond links their eq-runs folders,
# which is where the Mac job finds them. The baseline nets are the ones ks-1-lead0 rebuilt.
set -o pipefail
. "$(dirname "$0")/jlib.sh"
G=$OPC_OUT/pond-doubt; W=$HOME/premonition-pond; A=artifacts/claude-dir-pond-20260928; H=artifacts/claude-dir-h12-stop-20260928
BASE_CK=${POND_BASE_CK:-$KS_NETS}
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$G" "$W/$A/eq-runs"
for AR in a b c z; do for S in 0 1; do
  T=$HOME/premonition-pond-$AR/$A/eq-runs/pond-$AR-pre-s$S
  [ -d "$T" ] && ln -sfn "$T" "$W/$A/eq-runs/pond-$AR-pre-s$S"; done; done
echo "start $(date -u '+%F %T') UTC"; uptime; df -h "$HOME" | tail -1
FREE=$(freegb); [ "${FREE:-0}" -ge 2 ] || { echo "ABORT: under 2 GB free"; exit 4; }
[ -f "$OPC_R/$A/SEAL-code.sha256.txt" ] || { echo "WAITING: the pinned tree has no $A/SEAL-code.sha256.txt"; exit 5; }
for AR in a b c z; do for S in 0 1; do [ -f "$W/$A/eq-runs/pond-$AR-pre-s$S/adapt.json" ] && [ -f "$W/$A/eq-runs/pond-$AR-pre-s$S/k16384.pt" ] || echo "note: pond-$AR-pre-s$S not finished in $W; skipped"; done; done
[ -f "$W/$A/eq-runs/pond-b-pre-s0/adapt.json" ] || { echo "WAITING: no pond arm has finished in $W"; exit 5; }
unpack "$W" scripts artifacts/claude-fewex-20260927 $A $H || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
{ sha256sum -c $A/SEAL-code.sha256.txt; sha256sum -c $H/SEAL-code.sha256.txt; } > $A/seal-check-doubt.log 2>&1 || { cat $A/seal-check-doubt.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check-doubt.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
$PY scripts/claude_dir_h12_doubt.py selftest | tee $A/SELFTEST-doubt-mac.log
grep -q '"selftest": "ok"' $A/SELFTEST-doubt-mac.log || { echo "STOP: doubt selftest failed"; exit 7; }
mkdir -p $A/doubt
PIDS=""
for AR in a b c z; do for S in 0 1; do
  R=$A/eq-runs/pond-$AR-pre-s$S
  [ -f $R/adapt.json ] && [ -f $R/k16384.pt ] || continue
  nohup timeout -s ALRM 4800 $PY scripts/claude_dir_h12_doubt.py extract --run-dir $R --adapt-json $R/adapt.json --tag pond-$AR --out $A/doubt/doubt-items-pond-$AR-s$S.json --threads 1 > $A/doubt/extract-pond-$AR-s$S.log 2>&1 &
  echo "pond-$AR seed $S pid $!"
done; done
for S in 0 1; do
  if [ -f "$BASE_CK/loop-s$S-pre/k16384.pt" ]; then
    nohup timeout -s ALRM 4800 $PY scripts/claude_dir_h12_doubt.py extract --run-dir "$BASE_CK/loop-s$S-pre" --adapt-json artifacts/claude-fewex-20260927/eq-runs/loop-s$S-pre/adapt.json --tag baseline --out $A/doubt/doubt-items-baseline-s$S.json --threads 1 > $A/doubt/extract-baseline-s$S.log 2>&1 &
    echo "baseline seed $S pid $!"
  else echo "baseline seed $S: no checkpoints at $BASE_CK/loop-s$S-pre; skipped"; fi
done
wait
for f in $A/doubt/extract-*.log; do echo "== $f"; tail -3 "$f"; done
for AR in a b c z; do
  [ -f $A/doubt/doubt-items-pond-$AR-s0.json ] || continue
  echo "##### arm $AR (the table's tag column says 'h12': that is just its label for the first pattern)"
  $PY scripts/claude_dir_h12_doubt.py table --h12 "$A/doubt/doubt-items-pond-$AR-s{seed}.json" --baseline "$A/doubt/doubt-items-baseline-s{seed}.json" --out $A/doubt/DOUBT-TABLE-$AR.json | tee $A/doubt/DOUBT-TABLE-$AR.txt
done
sha256sum $A/doubt/*.json > $A/doubt/SHA256-doubt.txt
mkdir -p "$G/$A/doubt"; cp $A/doubt/* "$G/$A/doubt/"; cp $A/SELFTEST-doubt-mac.log $A/seal-check-doubt.log "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
