BASH-ONLY: yes
GPU: no (Mac CPU, strict fp32, $0, no training, no rental). LOAD-LIGHT: no (up to 4 single-thread processes). TIME CAP: 90 minutes. LABEL: h12-doubt.
DISK: 1
HELD-UNTIL: (a) job h12-stop-1-dev has finished on this Mac (both eq-runs/h12-pre-s{0,1}/adapt.json and their k*.pt exist under $HOME/premonition-h12; the job checks and prints WAITING otherwise); (b) origin/main holds artifacts/claude-dir-h12-stop-20260928/SEAL-code.sha256.txt including scripts/claude_dir_h12_doubt.py (the job refuses on a seal mismatch).
Owner job (helper H12, Claude, wrote this on 2026-09-28 21:37 UTC for the Director). Follow handoff/director-briefs/rules.md: additive only, no git commits or pushes by the job (the watcher pushes PUSH paths), blind panels never opened, never read or print keys or auth files, counts only, every deviation reported.
WHY: DESIGN.md section 9. Report-only diagnostic, no pass mark: per maze, does a late stop (cap hit, or after round 16) or an answer still changing over rounds 46-48 predict a wrong answer? It rescores the saved dev 9x9 checkpoints of the two H12 runs (and, if their checkpoints are still on this Mac, the baseline loop's two runs) and prints counts. No training, the holdout is not touched.
STOP RULE: any failed check, selftest or traceback: print it, run nothing further, exit non-zero.
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-h12; A=artifacts/claude-dir-h12-stop-20260928; REF=${H12_REF:-origin/main}
BASE_CK=${H12_BASE_CK:-/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927/eq-runs}
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 2 ] || { echo "ABORT: under 2 GB free"; exit 4; }
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
[ "$REF" = origin/main ] || git -C "$G" fetch -q origin "${REF#origin/}" || { echo "ABORT: fetch of $REF failed"; exit 4; }
git -C "$G" cat-file -e "$REF:$A/SEAL-code.sha256.txt" 2>/dev/null || { echo "WAITING: $REF has no $A/SEAL-code.sha256.txt"; exit 5; }
for S in 0 1; do [ -f "$W/$A/eq-runs/h12-pre-s$S/adapt.json" ] && [ -f "$W/$A/eq-runs/h12-pre-s$S/k16384.pt" ] || { echo "WAITING: h12-pre-s$S run is not finished in $W (run job h12-stop-1-dev first)"; exit 5; }; done
git -C "$G" archive "$REF" scripts artifacts/claude-fewex-20260927 $A | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
shasum -a 256 -c $A/SEAL-code.sha256.txt > $A/seal-check-doubt.log 2>&1 || { cat $A/seal-check-doubt.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check-doubt.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$PY scripts/claude_dir_h12_doubt.py selftest | tee $A/SELFTEST-doubt-mac.log
grep -q '"selftest": "ok"' $A/SELFTEST-doubt-mac.log || { echo "STOP: doubt selftest failed"; exit 7; }
mkdir -p $A/doubt
PIDS=""
for S in 0 1; do
  nohup perl -e 'alarm shift; exec @ARGV' 4800 $PY scripts/claude_dir_h12_doubt.py extract --run-dir $A/eq-runs/h12-pre-s$S --adapt-json $A/eq-runs/h12-pre-s$S/adapt.json --tag h12 --out $A/doubt/doubt-items-h12-s$S.json --threads 1 > $A/doubt/extract-h12-s$S.log 2>&1 &
  echo "h12 seed $S pid $!"
  if [ -f "$BASE_CK/loop-s$S-pre/k16384.pt" ]; then
    nohup perl -e 'alarm shift; exec @ARGV' 4800 $PY scripts/claude_dir_h12_doubt.py extract --run-dir "$BASE_CK/loop-s$S-pre" --adapt-json artifacts/claude-fewex-20260927/eq-runs/loop-s$S-pre/adapt.json --tag baseline --out $A/doubt/doubt-items-baseline-s$S.json --threads 1 > $A/doubt/extract-baseline-s$S.log 2>&1 &
    echo "baseline seed $S pid $!"
  else
    echo "baseline seed $S: no checkpoints at $BASE_CK/loop-s$S-pre; skipped (say so in the report)"
  fi
done
wait
for f in $A/doubt/extract-*.log; do echo "== $f"; tail -3 "$f"; done
for S in 0 1; do [ -f $A/doubt/doubt-items-h12-s$S.json ] || { echo "STOP: no H12 records for seed $S; report the first traceback in its log verbatim"; exit 8; }; done
$PY scripts/claude_dir_h12_doubt.py table --out $A/doubt/DOUBT-TABLE.json | tee $A/doubt/DOUBT-TABLE.txt
shasum -a 256 $A/doubt/*.json > $A/doubt/SHA256-doubt.txt
mkdir -p "$G/$A/doubt"; cp $A/doubt/* "$G/$A/doubt/"; cp $A/SELFTEST-doubt-mac.log $A/seal-check-doubt.log "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only, label diagnostic): for each of the four (tag, seed) whether every rung's recomputed counts matched adapt.json (the extract logs' consistent_with_harness lines; a mismatch is a finding, say so); the DOUBT-TABLE.txt lines for the pooled rows (k >= 64) and for k = 256 and 16,384 per tag and seed; the solved-short against solved-long mean rounds line; which baseline runs were skipped and why. Do not compute anything by hand; quote DOUBT-TABLE.txt.
PUSH: artifacts/claude-dir-h12-stop-20260928/doubt artifacts/claude-dir-h12-stop-20260928/SELFTEST-doubt-mac.log artifacts/claude-dir-h12-stop-20260928/seal-check-doubt.log
