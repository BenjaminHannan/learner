COMMON RULES (helper H3, Claude, wrote this task on 2026-09-28 19:20 UTC for the Director). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. Use at most 4 parallel processes. macOS has no `timeout` command (use perl alarm).
GPU: no (CPU only, fp32; the ruler forbids autocast and TF32). DISK: 2.
WORKDIR: run from the git worktree (the current directory). The job builds a private copy of origin/main in $HOME/premonition-h3 (committed files only) and works there, so a later job on the SAME machine finds the checkpoints. Checkpoints stay there and are never pushed.
LOAD-LIGHT: no (4 single-thread processes). TIME CAP: 120 minutes. LABEL: h3-holdout. MUST RUN ON THE SAME MACHINE AS JOBS 2 AND 3.
WAIT: start only if origin/main has artifacts/claude-dir-h3-design-20260928/dev-table.json and all four eq-runs/h3-{pre,fresh}-s{0,1}/adapt.json (the Director committed job 3's dev records BEFORE this job). Otherwise ABORT with WAITING. Also ABORT if any eq-runs/h3-*/holdout.started exists locally: a holdout is never re-opened after a partial run; report it instead.
WHY: PASSMARKS.md step 5. The one holdout pass per run, harness UNEDITED (`holdout` refuses unless the baseline's EQ-DEV-GATE.json says PASS, and refuses a second pass). Then the verdict arithmetic from PASSMARKS.md by scripts/claude_dir_h3_report.py.
Nothing is changed, tuned or re-run after these scores.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-h3
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
A=artifacts/claude-dir-h3-design-20260928
git -C "$G" show origin/main:$A/dev-table.json > /dev/null || { echo "WAITING: dev-table.json not on main"; exit 5; }
for S in 0 1; do for I in pre fresh; do git -C "$G" show origin/main:$A/eq-runs/h3-$I-s$S/adapt.json > /dev/null || { echo "WAITING: adapt.json $I s$S not on main"; exit 5; }; done; done
cd "$W" || exit 4
ls $A/eq-runs/h3-*/holdout.started 2>/dev/null && { echo "ABORT: a holdout was already started"; exit 7; }
git -C "$G" archive origin/main scripts artifacts/claude-fewex-20260927/EQ-DEV-GATE.json | tar -x -C "$W" || exit 4
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
for S in 0 1; do for I in pre fresh; do
  nohup perl -e 'alarm shift; exec @ARGV' 6600 $PY scripts/claude_fewex_eq_bench.py holdout --plugin claude_dir_h3_net --arm loop --seed $S --init $I --out $A/eq-runs/h3-$I-s$S --threads 1 > $A/eq-runs/h3-$I-s$S.holdout.log 2>&1 &
  echo "holdout seed $S init $I pid $!"
done; done
wait
for S in 0 1; do for I in pre fresh; do echo "== $I s$S"; tail -1 $A/eq-runs/h3-$I-s$S.holdout.log; ls $A/eq-runs/h3-$I-s$S/holdout.json; done; done
$PY scripts/claude_dir_h3_report.py --split holdout --h3 $A/eq-runs --loop "artifacts/claude-fewex-20260927/eq-runs/loop-s{seed}-pre" --plain "artifacts/claude-fewex-20260927/eq-runs/plain-s{seed}-pre" --out $A/holdout-table.json
for S in 0 1; do $PY scripts/claude_dir_h3_gate_report.py --ckpt $A/eq-runs/h3-pre-s$S/k64.pt --out $A/eq-runs/gate-k64-s$S.holdout-run.json --threads 1; done
for D in $A/eq-runs/h3-*-s?/; do cp $D/holdout.json "$G/$D/" 2>/dev/null; done
cp $A/eq-runs/*.holdout.log "$G/$A/eq-runs/"; cp $A/holdout-table.json "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply): the printed lines and the verdict line verbatim; the 9x9 holdout counts per rung (x of 300) for H3 and the loop, per seed; the failing marks per seed. State labels: shown for what the files say, suggested for causes, untested for the rest. Do not soften a REJECTED or NOT PROMOTED.
PUSH: artifacts/claude-dir-h3-design-20260928/holdout-table.json artifacts/claude-dir-h3-design-20260928/eq-runs   (holdout.json and logs only)
