#!/bin/bash
# opcpu job 3: handoff/queue/trn-decode-mac.md, science steps unchanged (see DEVIATIONS.md). Started by drive.sh after the ks nets exist.
# BM (the tree the job reads nets from) is built here: the Mac's loop / plain source.pt and plain k16384 sent by vstart.sh, and the loop k16384
# that ks-1-lead0 rebuilt (linked, not copied).
set -o pipefail
. "$(dirname "$0")/jlib.sh"
G=$OPC_OUT/trn-decode; W=$HOME/premonition-trn; A=artifacts/claude-dir-trn-20260929
BM=${TRN_BM:-$HOME/bm-trn}
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
mkdir -p "$G"
F=artifacts/claude-fewex-20260927
mkdir -p "$BM/$F/runs" "$BM/$F/eq-runs"
for S in 0 1; do for AR in loop plain; do
  mkdir -p "$BM/$F/runs/$AR-s$S" "$BM/$F/eq-runs/$AR-s$S-pre"
  [ -f "$OPC_IN/$F/runs/$AR-s$S/source.pt" ] && ln -sfn "$OPC_IN/$F/runs/$AR-s$S/source.pt" "$BM/$F/runs/$AR-s$S/source.pt"
done
  [ -f "$OPC_IN/$F/eq-runs/plain-s$S-pre/k16384.pt" ] && ln -sfn "$OPC_IN/$F/eq-runs/plain-s$S-pre/k16384.pt" "$BM/$F/eq-runs/plain-s$S-pre/k16384.pt"
  [ -f "$KS_NETS/loop-s$S-pre/k16384.pt" ] && ln -sfn "$KS_NETS/loop-s$S-pre/k16384.pt" "$BM/$F/eq-runs/loop-s$S-pre/k16384.pt"
done
echo "start $(date -u '+%F %T') UTC"; uptime
FREE=$(freegb); [ "${FREE:-0}" -ge 2 ] || { echo "ABORT: under 2 GB free"; exit 4; }
[ -f "$OPC_R/$A/SEAL-trn.sha256.txt" ] || { echo "WAITING: no seal in the pinned tree"; exit 5; }
for S in 0 1; do for AR in loop plain; do
  for P in runs/$AR-s$S/source.pt eq-runs/$AR-s$S-pre/k16384.pt; do [ -f "$BM/$F/$P" ] || { echo "MISSING-NET: $P"; exit 5; }; done
done; done
rm -rf "$W"; mkdir -p "$W"
unpack "$W" scripts $A || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
sha256sum -c $A/SEAL-trn.sha256.txt || { echo SEAL-MISMATCH; exit 6; }
$PY scripts/claude_dir_trn_decode.py selftest 2>&1 | tee $A/selftest.log
grep -q "trn selftest ok" $A/selftest.log || { echo "STOP: selftest failed"; exit 7; }
mkdir -p $A/run
for T in sums mazes; do
  nohup $PY scripts/claude_dir_trn_decode.py run --src "$BM" --out $A/run --tasks $T --threads 2 > $A/run/log-$T.txt 2>&1 &
  echo "$T pid $!"
done
wait
for T in sums mazes; do echo "== $T"; grep -c '^trn ' $A/run/log-$T.txt; tail -2 $A/run/log-$T.txt; done
cp $A/selftest.log $A/run/
# the Mac job never copies $A/run out of its work folder (its PUSH line would find nothing); here it is copied for the collect job
mkdir -p "$G/$A"; cp -R $A/run "$G/$A/"
[ -f $A/run/sums.json ] && [ -f $A/run/mazes.json ] || { echo "RUN-FAILED"; exit 1; }
echo "done $(date -u '+%F %T') UTC"
