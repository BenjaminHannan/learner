STATUS: HELD. DO NOT RUN (helper SL, 2026-09-28 from date -u). The Director releases it by deleting this line, after the checks under HELD-UNTIL below.
BASH-ONLY: yes
GPU: no (Mac CPU, strict fp32, $0, no training, no rental). LOAD-LIGHT: no (2 single-thread processes). TIME CAP: 120 minutes. LABEL: sl-read.
DISK: 1
HELD-UNTIL: (a) origin/main holds artifacts/claude-dir-sl-20260928 including SEAL-code.sha256.txt (the job refuses on a seal mismatch); (b) the qualified sources runs/qual-loop-s{0,1}/{source.pt,source.json} and the baseline checkpoints eq-runs/loop-s{0,1}-pre/k{64,256,1024,4096,16384}.pt exist on this Mac (the job checks and prints WAITING otherwise); (c) the Mac is not busy with another long CPU job (uptime).
Owner job (helper SL, Claude, for the Director). Follow handoff/director-briefs/rules.md: additive only, no git commits or pushes by the job (the watcher pushes PUSH paths), blind panels never opened, never read or print keys or auth files, counts only, every deviation reported.
WHY: artifacts/claude-dir-sl-20260928/DESIGN.md section 3 and PASSMARKS.md Parts A and B (marks written before any code). Two no-training reads on saved nets: Lead 3 (AUROC and coverage-versus-risk of five confidence signals for "this maze/sum/grid answer is wrong") and Lead 1 (stop when the answer is unchanged for 3 or 6 rounds; a ceiling only). Dev 9x9 mazes and fresh guard-seed sums and grids only; the holdout is NOT touched.
STOP RULE: any failed check, selftest or traceback: print it, run nothing further, exit non-zero.
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-sl; A=artifacts/claude-dir-sl-20260928; REF=${SL_REF:-origin/main}
SRC=${SL_SRC:-/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927/runs}
BASE_CK=${SL_BASE_CK:-/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927/eq-runs}
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 2 ] || { echo "ABORT: under 2 GB free"; exit 4; }
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
[ "$REF" = origin/main ] || git -C "$G" fetch -q origin "${REF#origin/}" || { echo "ABORT: fetch of $REF failed"; exit 4; }
git -C "$G" cat-file -e "$REF:$A/SEAL-code.sha256.txt" 2>/dev/null || { echo "WAITING: $REF has no $A/SEAL-code.sha256.txt"; exit 5; }
for S in 0 1; do
  [ -f "$SRC/qual-loop-s$S/source.pt" ] && [ -f "$SRC/qual-loop-s$S/source.json" ] || { echo "WAITING: no qualified source at $SRC/qual-loop-s$S"; exit 5; }
  for K in 64 256 1024 4096 16384; do [ -f "$BASE_CK/loop-s$S-pre/k$K.pt" ] || { echo "WAITING: no baseline checkpoint $BASE_CK/loop-s$S-pre/k$K.pt"; exit 5; }; done
done
mkdir -p "$W" && git -C "$G" archive "$REF" scripts artifacts/claude-fewex-20260927 $A | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
shasum -a 256 -c $A/SEAL-code.sha256.txt > $A/seal-check-read.log 2>&1 || { cat $A/seal-check-read.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check-read.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
for S in 0 1; do
  want=$(awk -v f="artifacts/claude-fewex-20260927/runs/qual-loop-s$S/source.json" '$2==f {print $1}' artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt)
  have=$(shasum -a 256 "$SRC/qual-loop-s$S/source.json" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "SOURCE-JSON-MISMATCH seed $S (sealed '$want', Mac '$have')"; exit 6; }
done
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$PY scripts/claude_dir_sl_read.py selftest | tee $A/SELFTEST-read-mac.log
grep -q '"selftest": "ok"' $A/SELFTEST-read-mac.log || { echo "STOP: read selftest failed"; exit 7; }
mkdir -p $A/read
for S in 0 1; do
  nohup perl -e 'alarm shift; exec @ARGV' 6000 $PY scripts/claude_dir_sl_read.py extract --source-dir "$SRC/qual-loop-s$S" --run-dir "$BASE_CK/loop-s$S-pre" --adapt-json artifacts/claude-fewex-20260927/eq-runs/loop-s$S-pre/adapt.json --seed $S --out $A/read/sl-records-s$S.json --threads 1 > $A/read/extract-s$S.log 2>&1 &
  echo "seed $S pid $! started $(date -u '+%F %T') UTC"
done
wait
for S in 0 1; do echo "== seed $S"; tail -3 $A/read/extract-s$S.log; [ -f $A/read/sl-records-s$S.json ] || { echo "STOP: no records for seed $S; report the first traceback in its log verbatim"; exit 8; }; done
$PY scripts/claude_dir_sl_read.py judge --out $A/read/READ-JUDGE.json | tee $A/read/READ-JUDGE.txt
shasum -a 256 $A/read/*.json > $A/read/SHA256-read.txt
mkdir -p "$G/$A/read"; cp $A/read/* "$G/$A/read/"; cp $A/SELFTEST-read-mac.log $A/seal-check-read.log "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only, label diagnostic, dev panels only, holdout unopened): whether every extract log line says consistent true (a false is a finding: say so and stop reading); the two verdict-word blocks from READ-JUDGE.txt (Part A word per signal, Part B word per rule) and, for k=64, 1024 and 16384 in each seed, the maze rule rows and the AUROC line; which panels were "not eligible" and why (fewer than 10 wrong). Do not compute any word by hand; quote READ-JUDGE.txt.
PUSH: artifacts/claude-dir-sl-20260928/read artifacts/claude-dir-sl-20260928/SELFTEST-read-mac.log artifacts/claude-dir-sl-20260928/seal-check-read.log
