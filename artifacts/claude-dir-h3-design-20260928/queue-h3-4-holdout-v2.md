COMMON RULES (helper H10, Claude, wrote this task on 2026-09-28 20:58 UTC for the Director; adapted from queue-h3-4-holdout.md by helper H3). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. macOS has no `timeout` command (use perl alarm).
STATUS: HELD. The Director releases it after queue-h3-3-dev-v2.md has run and its dev records (and, unless skipped on purpose, the three-draw sleep files of ADDENDUM-1 (b)) are committed. Do not run it while HELD. It replaces queue-h3-4-holdout.md (never run).
GPU: no (CPU only, fp32; the ruler forbids autocast and TF32). DISK: 2.
WORKDIR: run from the git worktree (the current directory). The job works in the private copy $HOME/premonition-h3v2 that jobs 2-v2 and 3-v2 built. Checkpoints stay there and are never pushed.
LOAD-LIGHT: no (six single-thread processes when `sysctl -n hw.ncpu` is at least 10, otherwise two waves: four then two). TIME CAP: 120 minutes when six run at once, 240 when two waves. LABEL: h3-holdout-v2. MUST RUN ON THE SAME MACHINE AS JOBS 2-v2 AND 3-v2.
WAIT: start only if origin/main has artifacts/claude-dir-h3-design-20260928/dev-table.json and all six eq-runs/{h3-pre,h3-fresh,h3c-pre}-s{0,1}/adapt.json (the Director committed job 3-v2's dev records BEFORE this job). Also required, one of: artifacts/claude-dir-h3-design-20260928/sleep-draws/sleep-draws-s0.json and sleep-draws-s1.json on origin/main (the three-draw sleeps, ADDENDUM-1 (b)), OR the Director's file artifacts/claude-dir-h3-design-20260928/SLEEPS-SKIPPED.txt on origin/main (then marks 4 are report-only and a PASS is worded "PASS (sleep gates not judged)"). Otherwise ABORT with WAITING. Also ABORT if any eq-runs/*/holdout.started exists locally: a holdout is never re-opened after a partial run; report it instead.
WHY: PASSMARKS.md step 5 with ADDENDUM-1. The one holdout pass per run (six runs: H3 v2 practised, H3 v2 fresh and the constant-g control, seeds 0 and 1), harness UNEDITED (`holdout` refuses unless the baseline's EQ-DEV-GATE.json says PASS, and refuses a second pass). Then the verdict arithmetic of ADDENDUM-1 by scripts/claude_dir_h3_report_add1.py (every gaining seed must break a gate to be REJECTED; F_few at least +5 over the loop is a required row; marks 4 on the three-draw means; the dead-gate flags and the control decide the mechanism sentence).
Nothing is changed, tuned or re-run after these scores.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-h3v2
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
A=artifacts/claude-dir-h3-design-20260928
git -C "$G" show origin/main:$A/dev-table.json > /dev/null || { echo "WAITING: dev-table.json not on main"; exit 5; }
for N in h3-pre-s0 h3-pre-s1 h3-fresh-s0 h3-fresh-s1 h3c-pre-s0 h3c-pre-s1; do git -C "$G" show origin/main:$A/eq-runs/$N/adapt.json > /dev/null || { echo "WAITING: adapt.json $N not on main"; exit 5; }; done
DRAWS=""
if git -C "$G" show origin/main:$A/sleep-draws/sleep-draws-s0.json > /dev/null 2>&1 && git -C "$G" show origin/main:$A/sleep-draws/sleep-draws-s1.json > /dev/null 2>&1; then
  DRAWS="--sleep-draws $A/sleep-draws"; echo "sleep draws found on main: marks 4 are judged on the three-draw means"
elif git -C "$G" show origin/main:$A/SLEEPS-SKIPPED.txt > /dev/null 2>&1; then
  echo "SLEEPS-SKIPPED.txt found on main: marks 4 are report-only"
else
  echo "WAITING: neither the three-draw sleep files nor SLEEPS-SKIPPED.txt is on main"; exit 5
fi
cd "$W" || exit 4
ls $A/eq-runs/*/holdout.started 2>/dev/null && { echo "ABORT: a holdout was already started"; exit 7; }
[ -n "$DRAWS" ] && { git -C "$G" archive origin/main $A/sleep-draws | tar -x -C "$W" || exit 4; }
git -C "$G" archive origin/main scripts artifacts/claude-fewex-20260927/EQ-DEV-GATE.json | tar -x -C "$W" || exit 4
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
NC=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
hold() {  # $1 plugin, $2 seed, $3 init, $4 run name
  nohup perl -e 'alarm shift; exec @ARGV' 6600 $PY scripts/claude_fewex_eq_bench.py holdout --plugin $1 --arm loop --seed $2 --init $3 --out $A/eq-runs/$4 --threads 1 > $A/eq-runs/$4.holdout.log 2>&1 &
  echo "holdout $4 pid $!"
}
for S in 0 1; do for I in pre fresh; do hold claude_dir_h3_net_v2 $S $I h3-$I-s$S; done; done
if [ "$NC" -ge 10 ]; then
  for S in 0 1; do hold claude_dir_h3_net_v2_const $S pre h3c-pre-s$S; done; wait
else
  wait; for S in 0 1; do hold claude_dir_h3_net_v2_const $S pre h3c-pre-s$S; done; wait
fi
for N in h3-pre-s0 h3-pre-s1 h3-fresh-s0 h3-fresh-s1 h3c-pre-s0 h3c-pre-s1; do echo "== $N"; tail -1 $A/eq-runs/$N.holdout.log; ls $A/eq-runs/$N/holdout.json; done
$PY scripts/claude_dir_h3_report_add1.py --split holdout --h3 $A/eq-runs --loop "artifacts/claude-fewex-20260927/eq-runs/loop-s{seed}-pre" --plain "artifacts/claude-fewex-20260927/eq-runs/plain-s{seed}-pre" --control $A/eq-runs --gate-reports $A/eq-runs $DRAWS --out $A/holdout-table.json
for S in 0 1; do $PY scripts/claude_dir_h3_gate_report_v2.py --ckpt $A/eq-runs/h3-pre-s$S/k64.pt --out $A/eq-runs/gate-k64-s$S.holdout-run.json --threads 1; done
for D in $A/eq-runs/h3-*-s?/ $A/eq-runs/h3c-*-s?/; do cp $D/holdout.json "$G/$D/" 2>/dev/null; done
cp $A/eq-runs/*.holdout.log "$G/$A/eq-runs/"; cp $A/holdout-table.json "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
NOTE for the Director (not a step): the report reads the dead-gate flags from gate-k64-s{seed}.json and gate-k16384-s{seed}.json written by job 3-v2 (dev checkpoints of the practised H3), the same files whether or not the holdout has run. The loop in the F_few and sleep-gate comparisons is the baseline's recorded eq-runs/loop-s{seed}-pre; if the loop's sleep draws had to be rebuilt (ADDENDUM-1 (b)), the draw files say so and the report shows it under sleep_draw_detail.
REPORT (final reply): the printed lines and the verdict line and mechanism line verbatim; the 9x9 holdout counts per rung (x of 300) for H3, the constant-g control and the loop, per seed; the failing marks per seed; F_few per arm. State labels: shown for what the files say, suggested for causes, untested for the rest. Do not soften a REJECTED or NOT PROMOTED.
PUSH: artifacts/claude-dir-h3-design-20260928/holdout-table.json artifacts/claude-dir-h3-design-20260928/eq-runs   (holdout.json and logs only)
