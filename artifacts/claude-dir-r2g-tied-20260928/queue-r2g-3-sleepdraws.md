COMMON RULES (helper R2g, Claude, wrote this task on 2026-09-28 for the Director; adapted from the H3 v2 queue files by helpers H3 and H10). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. macOS has no `timeout` command (use perl alarm).
STATUS: HELD. The Director releases it after queue-r2g-2-dev.md has run and its dev records are committed. Do not run it while HELD.
GPU: no (CPU only, fp32). DISK: 2.
WORKDIR: run from the git worktree; works in $HOME/premonition-r2g (same machine as jobs 1 and 2).
LOAD-LIGHT: no (four single-thread processes). TIME CAP: 120 minutes (about 255 s per sleep, distill RESULTS.md; 3 draws x 2 branches x 2 seeds x 2 sides = 24 sleeps, of which 8 are draw 0 that only repeat the recorded sleep; untested). LABEL: r2g-sleepdraws.
WHY: PASSMARKS.md row 5 (H10 amendment (b) of the H3 ADDENDUM-1): three sleep draws of R2g and of the loop per seed and branch (k = 64 and 16,384), counts of 200. The loop's side needs the BASELINE run folder that still holds adapt.json, k64.pt and k16384.pt (not in the repo). Search below. If it is missing on this machine, do NOT rebuild the loop (the distill test showed a rebuild is not the ruler's net): report it and STOP; the Director then commits SLEEPS-SKIPPED.txt (row 5 becomes report-only, and a PASS reads "PASS (sleep gates not judged)").
Draw 0 must equal the harness's recorded sleep in adapt.json exactly; the script prints and records `draw0_matches`; if false for a side and seed, the draws for that seed are void (report, do not use).
STOP RULE: any traceback: report the first one verbatim.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-r2g
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
A=artifacts/claude-dir-r2g-tied-20260928
for N in h3-pre-s0 h3-pre-s1; do [ -f "$W/$A/eq-runs/$N/k16384.pt" ] || { echo "ABORT: $N checkpoints missing in $W (same machine as job 2)"; exit 6; }; done
git -C "$G" archive origin/main scripts $A artifacts/claude-fewex-20260927 | tar -x -C "$W" || exit 4
cd "$W" || exit 4
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
mkdir -p $A/sleep-draws
for S in 0 1; do
  LR=$(find "$HOME" -maxdepth 6 -path "*eq-runs/loop-s$S-pre/k16384.pt" 2>/dev/null | head -1)
  [ -n "$LR" ] || { echo "STOP: baseline loop checkpoints for seed $S not found on this machine: Director commits SLEEPS-SKIPPED.txt"; exit 7; }
  LD=$(dirname "$LR"); [ -f "$LD/k64.pt" ] && [ -f "$LD/adapt.json" ] || { echo "STOP: $LD lacks k64.pt or adapt.json"; exit 7; }
  echo "loop run folder seed $S: $LD"
done
run() {  # $1 plugin, $2 seed, $3 run dir, $4 out
  nohup perl -e 'alarm shift; exec @ARGV' 6600 $PY scripts/claude_dir_r2g_sleepdraws.py --plugin $1 --arm loop --seed $2 --run-dir "$3" --out $4 --threads 1 > $4.log 2>&1 &
}
for S in 0 1; do
  LD=$(dirname "$(find "$HOME" -maxdepth 6 -path "*eq-runs/loop-s$S-pre/k16384.pt" | head -1)")
  run claude_dir_r2g_net $S $A/eq-runs/h3-pre-s$S $A/sleep-draws/design-s$S.json
  run claude_fewex_net $S "$LD" $A/sleep-draws/loop-s$S.json
done
wait
for S in 0 1; do
  cat $A/sleep-draws/design-s$S.json.log $A/sleep-draws/loop-s$S.json.log
  python3 scripts/claude_dir_r2g_sleepdraws.py merge --h3 $A/sleep-draws/design-s$S.json --loop $A/sleep-draws/loop-s$S.json --out $A/sleep-draws/sleep-draws-s$S.json
done
mkdir -p "$G/$A/sleep-draws"; cp $A/sleep-draws/*.json $A/sleep-draws/*.log "$G/$A/sleep-draws/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply): the printed lines per side, seed and branch (draws vs recorded, draw0_matches); whether the merge succeeded for each seed; where the loop's folders were.
PUSH: artifacts/claude-dir-r2g-tied-20260928/sleep-draws   (json and logs only)
