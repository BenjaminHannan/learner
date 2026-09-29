#!/bin/bash
# opcpu job 2: handoff/queue/s2think-1-mac.md, science steps unchanged (see DEVIATIONS.md). Started by drive.sh after the ks nets exist.
set -o pipefail
. "$(dirname "$0")/jlib.sh"
G=$OPC_OUT/s2think; W=$HOME/premonition-s2think; A=artifacts/claude-sweep-s2-20260929
FEW=${S2_SRC:-$OPC_IN/artifacts/claude-fewex-20260927}
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$G"
echo "start $(date -u '+%F %T') UTC"; uptime; df -h "$HOME" | tail -1
FREE=$(freegb); [ "${FREE:-0}" -ge 2 ] || { echo "ABORT: under 2 GB free"; exit 4; }
[ -f "$OPC_R/$A/SEAL-code.sha256.txt" ] || { echo "WAITING: the pinned tree has no $A/SEAL-code.sha256.txt"; exit 5; }
unpack "$W" scripts artifacts/claude-fewex-20260927 $A || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
sha256sum -c $A/SEAL-code.sha256.txt > $A/seal-check.log 2>&1 || { cat $A/seal-check.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
$PY scripts/claude_sweep_s2_think.py selftest | tee $A/SELFTEST-mac.log
grep -q '"selftest": "ok"' $A/SELFTEST-mac.log || { echo "STOP: selftest failed"; exit 7; }
# where the nets may live (first hit wins): the ruler's own folder, the keep-old-skills rebuild folder ($HOME/premonition-ks/nets), other premonition-* folders
find_ck() {  # seed, name -> path or empty
  for d in "$FEW/eq-runs/loop-s$1-pre" "$HOME/premonition-ks/nets/loop-s$1-pre" "$HOME/premonition-models/fewex/loop-s$1-pre"; do
    [ -f "$d/$2.pt" ] && { echo "$d/$2.pt"; return; }
  done
  find "$HOME"/premonition-* "$FEW" -maxdepth 6 -path "*loop-s$1-pre/$2.pt" -type f 2>/dev/null | head -1
}
mkdir -p $A/traces $A/logs
trace_seed() {
  S=$1
  [ -f "$FEW/runs/qual-loop-s$S/source.json" ] || { echo "seed $S: no source.json at $FEW/runs/qual-loop-s$S"; return 0; }
  want=$(awk -v f="artifacts/claude-fewex-20260927/runs/qual-loop-s$S/source.json" '$2==f {print $1}' artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt)
  have=$(sha256sum "$FEW/runs/qual-loop-s$S/source.json" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "SOURCE-JSON-MISMATCH seed $S"; return 6; }
  for N in k64 sleep64 k16384 sleep16384 k0 k256 k1024 k4096; do
    OUT=$A/traces/s$S-$N.json
    [ -f "$OUT" ] && { echo "seed $S $N: already traced"; continue; }
    if [ "$N" = k0 ]; then CK="$FEW/runs/qual-loop-s$S/source.pt"; [ -f "$CK" ] || CK=""; else CK=$(find_ck $S $N); fi
    [ -n "$CK" ] || { echo "MISSING seed $S $N"; continue; }
    case $N in sleep64) ALT=$(find_ck $S k64);; sleep16384) ALT=$(find_ck $S k16384);; k64) ALT=$(find_ck $S sleep64);; k16384) ALT=$(find_ck $S sleep16384);; *) ALT="";; esac
    echo "seed $S $N ck=$CK sha=$(sha256sum "$CK" | awk '{print $1}') alt=${ALT:-none}"
    $PY scripts/claude_sweep_s2_think.py trace --seed $S --name $N --ckpt "$CK" ${ALT:+--alt-ckpt "$ALT"} \
      --source-json "$FEW/runs/qual-loop-s$S/source.json" --adapt-json artifacts/claude-fewex-20260927/eq-runs/loop-s$S-pre/adapt.json \
      --out $OUT --threads 1 > $A/logs/s$S-$N.log 2>&1 || { echo "FAILED seed $S $N (first lines of its log follow)"; head -30 $A/logs/s$S-$N.log; rm -f $OUT; return 8; }
    tail -1 $A/logs/s$S-$N.log
  done
}
export -f find_ck 2>/dev/null
for S in 0 1; do trace_seed $S > $A/logs/run-s$S.log 2>&1 & done
wait
cat $A/logs/run-s0.log $A/logs/run-s1.log
grep -q '^FAILED\|^SOURCE-JSON-MISMATCH' $A/logs/run-s0.log $A/logs/run-s1.log && { echo "STOP: a trace failed or a source did not match"; exit 8; }
ls $A/traces/*.json >/dev/null 2>&1 || { echo "WAITING: no saved net was found on this box"; exit 5; }
$PY scripts/claude_sweep_s2_think.py judge --records $A/traces --out $A/JUDGE.json | tee $A/JUDGE.txt
sha256sum $A/traces/*.json $A/JUDGE.json > $A/SHA256-run.txt
mkdir -p "$G/$A"; cp -R $A/traces $A/logs $A/JUDGE.json $A/JUDGE.txt $A/SHA256-run.txt $A/SELFTEST-mac.log $A/seal-check.log "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
