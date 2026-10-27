BASH-ONLY: yes
GPU: no (Mac CPU, strict fp32, $0, no training, no rental). LOAD-LIGHT: no (up to 4 single-thread processes at once is fine; there can be up to 10 extractions, run them in order of the loop above). TIME CAP: 120 minutes. LABEL: pond-doubt.
DISK: 1
HELD-UNTIL: at least one of the jobs pond-a/b/c/z has finished on this Mac (the job checks and prints WAITING otherwise); origin/main (or POND_REF) holds the pond SEAL and H12's doubt script (the job refuses on a seal mismatch). Nothing is held for Ben.
Owner job (helper pond, Claude, thread "Charge for thinking"). Follow handoff/director-briefs/rules.md: additive only, no git by the job, blind panels never opened, never read or print keys or auth files, counts only, every deviation reported.
WHY: the Director asked to reuse H12's doubt check (report-only, no pass mark): per maze, does a late stop (cap hit, or after round 16) or an answer still changing over rounds 46-48 predict a wrong answer, now for the pond-trained stops beside the baseline's? It rescores saved dev 9x9 checkpoints (no training, holdout not touched) with H12's own script `scripts/claude_dir_h12_doubt.py`, unedited.
STOP RULE: any failed check, selftest or traceback: print it, run nothing further, exit non-zero.
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-pond; A=artifacts/claude-dir-pond-20260928; H=artifacts/claude-dir-h12-stop-20260928; REF=${POND_REF:-origin/main}
BASE_CK=${POND_BASE_CK:-/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927/eq-runs}
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 2 ] || { echo "ABORT: under 2 GB free"; exit 4; }
{ git -C "$G" fetch -q origin main || { sleep 30; git -C "$G" fetch -q origin main; } || { sleep 120; git -C "$G" fetch -q origin main; }; } || { echo "ABORT: fetch failed"; exit 4; }
[ "$REF" = origin/main ] || git -C "$G" fetch -q origin "${REF#origin/}" || { echo "ABORT: fetch of $REF failed"; exit 4; }
git -C "$G" cat-file -e "$REF:$A/SEAL-code.sha256.txt" 2>/dev/null || { echo "WAITING: $REF has no $A/SEAL-code.sha256.txt"; exit 5; }
for AR in a b c z; do for S in 0 1; do [ -f "$W/$A/eq-runs/pond-$AR-pre-s$S/adapt.json" ] && [ -f "$W/$A/eq-runs/pond-$AR-pre-s$S/k16384.pt" ] || echo "note: pond-$AR-pre-s$S not finished in $W; skipped"; done; done
[ -f "$W/$A/eq-runs/pond-b-pre-s0/adapt.json" ] || { echo "WAITING: no pond arm has finished in $W"; exit 5; }
git -C "$G" archive "$REF" scripts artifacts/claude-fewex-20260927 $A $H | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
{ shasum -a 256 -c $A/SEAL-code.sha256.txt; shasum -a 256 -c $H/SEAL-code.sha256.txt; } > $A/seal-check-doubt.log 2>&1 || { cat $A/seal-check-doubt.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check-doubt.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$PY scripts/claude_dir_h12_doubt.py selftest | tee $A/SELFTEST-doubt-mac.log
grep -q '"selftest": "ok"' $A/SELFTEST-doubt-mac.log || { echo "STOP: doubt selftest failed"; exit 7; }
mkdir -p $A/doubt
PIDS=""
for AR in a b c z; do for S in 0 1; do
  R=$A/eq-runs/pond-$AR-pre-s$S
  [ -f $R/adapt.json ] && [ -f $R/k16384.pt ] || continue
  nohup perl -e 'alarm shift; exec @ARGV' 4800 $PY scripts/claude_dir_h12_doubt.py extract --run-dir $R --adapt-json $R/adapt.json --tag pond-$AR --out $A/doubt/doubt-items-pond-$AR-s$S.json --threads 1 > $A/doubt/extract-pond-$AR-s$S.log 2>&1 &
  echo "pond-$AR seed $S pid $!"
done; done
for S in 0 1; do
  if [ -f "$BASE_CK/loop-s$S-pre/k16384.pt" ]; then
    nohup perl -e 'alarm shift; exec @ARGV' 4800 $PY scripts/claude_dir_h12_doubt.py extract --run-dir "$BASE_CK/loop-s$S-pre" --adapt-json artifacts/claude-fewex-20260927/eq-runs/loop-s$S-pre/adapt.json --tag baseline --out $A/doubt/doubt-items-baseline-s$S.json --threads 1 > $A/doubt/extract-baseline-s$S.log 2>&1 &
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
shasum -a 256 $A/doubt/*.json > $A/doubt/SHA256-doubt.txt
mkdir -p "$G/$A/doubt"; cp $A/doubt/* "$G/$A/doubt/"; cp $A/SELFTEST-doubt-mac.log $A/seal-check-doubt.log "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only, label diagnostic): per (tag, seed) whether every rung's recomputed counts matched adapt.json (the extract logs' consistent_with_harness lines; a mismatch is a finding); the DOUBT-TABLE-<arm>.txt lines for the pooled rows (k >= 64) per arm and seed; which arms or baseline runs were skipped and why. Quote the table; compute nothing by hand.
PUSH: artifacts/claude-dir-pond-20260928/doubt artifacts/claude-dir-pond-20260928/SELFTEST-doubt-mac.log artifacts/claude-dir-pond-20260928/seal-check-doubt.log
