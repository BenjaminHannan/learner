COMMON RULES (helper R1G, Claude, wrote this task on 2026-09-28 for the Director; adapted from the H3 v2 queue files by helper H10). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. macOS has no `timeout` command (use perl alarm).
STATUS: HELD. The Director releases it (see WAIT). Do not run it while HELD.
GPU: no (CPU only, fp32; the ruler forbids autocast and TF32). DISK: 2.
WORKDIR: run from the git worktree (the current directory). The job builds/uses a private copy of origin/main in $HOME/premonition-r1g (committed files only). Checkpoints stay there and are never pushed.
LOAD-LIGHT: no (four single-thread processes). TIME CAP: 240 minutes for holdouts; the three-draw sleeps are 12 sleeps per arm and seed (see below). LABEL: r1g-holdout. MUST RUN ON THE SAME MACHINE AS jobs 1 and 2.
WAIT: start only if origin/main has artifacts/claude-dir-r1g-20260928/dev-table.json and eq-runs/r1g-{pre,fresh}-s{0,1}/adapt.json and credit/credit-s{0,1}.json (the Director committed job 2's dev records BEFORE this job). Abort with WAITING otherwise. ABORT if any eq-runs/*/holdout.started exists locally: a holdout is never re-opened after a partial run; report it instead.
SLEEP DRAWS (PASSMARKS mark 4): the driver scripts/claude_dir_r1g_sleepdraws.py makes 3 draws per arm, seed and branch (k = 64 and 16,384): 2 arms x 2 seeds x 2 branches x 3 draws = 24 sleeps, about 255 s each on one CPU thread (distill RESULTS.md figure for the H3 plan; untested here), so about 100 core-minutes for the new draws (draw 0 repeats the harness sleep as the equality check). The R1g draws use its own k64.pt and k16384.pt. The LOOP draws need the loop's k64.pt and k16384.pt from the baseline runs, which are NOT in the repo: set LOOP_RUN_S0 and LOOP_RUN_S1 to those folders (each with adapt.json and the two .pt files) if they still exist on this machine. If they do not, this job SKIPS the sleep draws, writes SLEEPS-SKIPPED.txt into the job folder and the Director decides (the alternative is a rebuild of the loop with `--plugin claude_fewex_net --init pre`, about 169 minutes per seed, which the distill run showed is not the ruler's own net; never mix rebuilt and recorded loop numbers). Marks 4 are then report-only and a PASS reads "PASS (sleep gates not judged)".
WHY: PASSMARKS.md order steps 4 and 5. One holdout pass per run (four runs: R1g practised and fresh, seeds 0 and 1), harness UNEDITED (`holdout` refuses unless the baseline's EQ-DEV-GATE.json says PASS, and refuses a second pass). Then the verdict by scripts/claude_dir_r1g_report.py. Nothing is changed, tuned or re-run after these scores.
STOP RULE: any traceback: report the first one verbatim, run nothing else.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-r1g; A=artifacts/claude-dir-r1g-20260928
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
git -C "$G" show origin/main:$A/dev-table.json > /dev/null || { echo "WAITING: dev-table.json not on main"; exit 5; }
for N in r1g-pre-s0 r1g-pre-s1 r1g-fresh-s0 r1g-fresh-s1; do git -C "$G" show origin/main:$A/eq-runs/$N/adapt.json > /dev/null || { echo "WAITING: adapt.json $N not on main"; exit 5; }; done
for S in 0 1; do git -C "$G" show origin/main:$A/credit/credit-s$S.json > /dev/null || { echo "WAITING: credit-s$S.json not on main"; exit 5; }; done
cd "$W" || exit 4
ls $A/eq-runs/*/holdout.started 2>/dev/null && { echo "ABORT: a holdout was already started"; exit 7; }
git -C "$G" archive origin/main scripts $A/credit artifacts/claude-fewex-20260927/EQ-DEV-GATE.json | tar -x -C "$W" || exit 4
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
NC=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
# 1. three-draw sleeps (before the holdout, so nothing here can see a holdout score)
DRAWS=""
mkdir -p $A/sleep-draws
if [ -n "$LOOP_RUN_S0" ] && [ -n "$LOOP_RUN_S1" ] && [ -f "$LOOP_RUN_S0/k64.pt" ] && [ -f "$LOOP_RUN_S0/k16384.pt" ] && [ -f "$LOOP_RUN_S1/k64.pt" ] && [ -f "$LOOP_RUN_S1/k16384.pt" ]; then
  for S in 0 1; do
    eval L=\$LOOP_RUN_S$S
    for K in 64 16384; do
      $PY scripts/claude_dir_r1g_sleepdraws.py draws --plugin claude_dir_r1g_net --run $A/eq-runs/r1g-pre-s$S --k $K --out $A/sleep-draws/r1g-s$S-k$K.json --threads 1 &
      $PY scripts/claude_dir_r1g_sleepdraws.py draws --plugin claude_fewex_net --run $L --k $K --out $A/sleep-draws/loop-s$S-k$K.json --threads 1 &
    done
    wait
    $PY scripts/claude_dir_r1g_sleepdraws.py merge --seed $S --dir $A/sleep-draws --out $A/sleep-draws/sleep-draws-s$S.json || { echo "draws void for seed $S: see message above"; }
  done
  [ -f $A/sleep-draws/sleep-draws-s0.json ] && [ -f $A/sleep-draws/sleep-draws-s1.json ] && DRAWS="--sleep-draws $A/sleep-draws"
else
  echo "loop checkpoints not on this machine: sleep draws SKIPPED" | tee $A/SLEEPS-SKIPPED.txt
fi
# 2. holdout passes
hold() {  # $1 seed, $2 init
  nohup perl -e 'alarm shift; exec @ARGV' 6600 $PY scripts/claude_fewex_eq_bench.py holdout --plugin claude_dir_r1g_net --arm loop --seed $1 --init $2 --out $A/eq-runs/r1g-$2-s$1 --threads 1 > $A/eq-runs/r1g-$2-s$1.holdout.log 2>&1 &
  echo "holdout r1g-$2-s$1 pid $!"
}
for S in 0 1; do for I in pre fresh; do hold $S $I; done; done
wait
for N in r1g-pre-s0 r1g-pre-s1 r1g-fresh-s0 r1g-fresh-s1; do echo "== $N"; tail -1 $A/eq-runs/$N.holdout.log; ls $A/eq-runs/$N/holdout.json; done
# 3. the verdict (use-s{seed}.json came with the archived credit folder)
$PY scripts/claude_dir_r1g_report.py --split holdout --runs $A/eq-runs --loop "artifacts/claude-fewex-20260927/eq-runs/loop-s{seed}-pre" --plain "artifacts/claude-fewex-20260927/eq-runs/plain-s{seed}-pre" --credit $A/credit --use $A/credit $DRAWS --out $A/holdout-table.json
for D in $A/eq-runs/r1g-*-s?/; do cp $D/holdout.json "$G/$D/" 2>/dev/null; done
mkdir -p "$G/$A/sleep-draws"; cp $A/sleep-draws/*.json "$G/$A/sleep-draws/" 2>/dev/null; cp $A/SLEEPS-SKIPPED.txt "$G/$A/" 2>/dev/null
cp $A/eq-runs/*.holdout.log "$G/$A/eq-runs/"; cp $A/holdout-table.json "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
NOTE for the Director (not a step): the use-s{seed}.json files come from job 2 (they read only the practised and k = 16,384 checkpoints, no holdout) and travel in the credit folder, so job 2's PUSH must be on main before this job. The loop in F_few and the sleep comparisons is the baseline's recorded eq-runs/loop-s{seed}-pre.
REPORT (final reply): the printed lines and the verdict line and mechanism line verbatim; the 9x9 holdout counts per rung (x of 300) for R1g practised, R1g fresh and the loop, per seed; the failing marks per seed; F_few per arm; whether draw 0 matched the recorded sleep. Labels: shown for what the files say, suggested for causes, untested for the rest. Do not soften a REJECTED or NOT PROMOTED.
PUSH: artifacts/claude-dir-r1g-20260928/holdout-table.json artifacts/claude-dir-r1g-20260928/eq-runs (holdout.json and logs only) artifacts/claude-dir-r1g-20260928/sleep-draws artifacts/claude-dir-r1g-20260928/SLEEPS-SKIPPED.txt
