STATUS: HELD. Real dependency: the job is one-shot and exits WAITING (5) without the adapted loop checkpoints; the Director removes this line once ks-1-lead0-mac-r2 has rebuilt them (2026-09-29).
BASH-ONLY: yes
GPU: no (Mac CPU, strict fp32, $0, no training, no rental, no BensPC). LOAD-LIGHT: no (2 single-thread processes, about 3 minutes per net). TIME CAP: 120 minutes. LABEL: s2think.
DISK: 1
Owner job (sweep helper S2 "Watch it think", Claude, wrote this on 2026-09-29 for the Director). Follow handoff/director-briefs/rules.md: additive only, no git commits or pushes by the job (the watcher pushes PUSH paths), blind panels and the holdout never opened, never read or print keys or auth files, counts only, every deviation reported.
WHY: artifacts/claude-sweep-s2-20260929/PASSMARKS.md (marks written before any real net was read). Zero training: per-round state movement, stop logit, answer flips and two-start agreement of saved loop nets on the 300 dev 9x9 mazes, plus a 2x2 of the stop head against the state for the sleep nets. It reads whichever nets exist; a missing net is listed and skipped (rerun the job later to fill in; finished nets are not redone). It does NOT rebuild anything. The nets must be the committed ones: a net whose dev counts differ from the committed adapt.json is labelled MISMATCH and kept out of every verdict word.
STOP RULE: a failed seal, selftest or traceback: print it, run nothing further, exit non-zero. No net at all: print WAITING, exit 5.
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-s2think; A=artifacts/claude-sweep-s2-20260929; REF=${S2_REF:-origin/main}
FEW=${S2_SRC:-/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927}
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 2 ] || { echo "ABORT: under 2 GB free"; exit 4; }
{ git -C "$G" fetch -q origin main || { sleep 30; git -C "$G" fetch -q origin main; } || { sleep 120; git -C "$G" fetch -q origin main; }; } || { echo "ABORT: fetch failed"; exit 4; }
git -C "$G" cat-file -e "$REF:$A/SEAL-code.sha256.txt" 2>/dev/null || { echo "WAITING: $REF has no $A/SEAL-code.sha256.txt"; exit 5; }
mkdir -p "$W" && git -C "$G" archive "$REF" scripts artifacts/claude-fewex-20260927 $A | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
shasum -a 256 -c $A/SEAL-code.sha256.txt > $A/seal-check.log 2>&1 || { cat $A/seal-check.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$PY scripts/claude_sweep_s2_think.py selftest | tee $A/SELFTEST-mac.log
grep -q '"selftest": "ok"' $A/SELFTEST-mac.log || { echo "STOP: selftest failed"; exit 7; }
# where the nets may live (first hit wins): the ruler's own folder, the keep-old-skills rebuild folder, other premonition-* folders
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
  have=$(shasum -a 256 "$FEW/runs/qual-loop-s$S/source.json" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "SOURCE-JSON-MISMATCH seed $S"; return 6; }
  for N in k64 sleep64 k16384 sleep16384 k0 k256 k1024 k4096; do
    OUT=$A/traces/s$S-$N.json
    [ -f "$OUT" ] && { echo "seed $S $N: already traced"; continue; }
    if [ "$N" = k0 ]; then CK="$FEW/runs/qual-loop-s$S/source.pt"; [ -f "$CK" ] || CK=""; else CK=$(find_ck $S $N); fi
    [ -n "$CK" ] || { echo "MISSING seed $S $N"; continue; }
    case $N in sleep64) ALT=$(find_ck $S k64);; sleep16384) ALT=$(find_ck $S k16384);; k64) ALT=$(find_ck $S sleep64);; k16384) ALT=$(find_ck $S sleep16384);; *) ALT="";; esac
    echo "seed $S $N ck=$CK sha=$(shasum -a 256 "$CK" | awk '{print $1}') alt=${ALT:-none}"
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
ls $A/traces/*.json >/dev/null 2>&1 || { echo "WAITING: no saved net was found on this Mac"; exit 5; }
$PY scripts/claude_sweep_s2_think.py judge --records $A/traces --out $A/JUDGE.json | tee $A/JUDGE.txt
shasum -a 256 $A/traces/*.json $A/JUDGE.json > $A/SHA256-run.txt
mkdir -p "$G/$A"; cp -R $A/traces $A/logs $A/JUDGE.json $A/JUDGE.txt $A/SHA256-run.txt $A/SELFTEST-mac.log $A/seal-check.log "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only, dev panel only, holdout unopened): the MISSING lines; for each traced net whether it printed consistent true (a false is a finding: say so, do not read that net further); the whole of JUDGE.txt (per-net words with b c d and movement, the aggregate CONVERGES / DRIFTS / blocker counts / WRONG lines, and the sleep 2x2 lines). Do not compute a word by hand; quote JUDGE.txt.
PUSH: artifacts/claude-sweep-s2-20260929/traces artifacts/claude-sweep-s2-20260929/logs artifacts/claude-sweep-s2-20260929/JUDGE.json artifacts/claude-sweep-s2-20260929/JUDGE.txt artifacts/claude-sweep-s2-20260929/SHA256-run.txt artifacts/claude-sweep-s2-20260929/SELFTEST-mac.log artifacts/claude-sweep-s2-20260929/seal-check.log
