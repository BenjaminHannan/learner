COMMON RULES (helper Huginn ideas, Claude, wrote this 2026-09-29 for the Director; adapted from the H3 v2 jobs). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss.
STATUS: HELD (real dependency: needs job hist-1-practice's four source.json committed with "v1_pass": true, on the SAME machine).
GPU: no (CPU only, fp32). DISK: 2.
WORKDIR: run from the git worktree. Works in $HOME/premonition-hist (where hist-1-practice left the checkpoints). LOAD-LIGHT: no (four single-thread processes). TIME CAP: 330 minutes. LABEL: hist-dev.
WHY: artifacts/claude-dir-hist-20260929/PASSMARKS.md step 3. The dev ladders of the equal-practice ruler, harness unedited, for HIST and CTRL-W1, seeds 0 and 1 (`--init pre`). The holdout is NOT touched. No change of any kind after a dev score is seen.
STOP RULE: any traceback: report the first one verbatim, run nothing else.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-hist; A=artifacts/claude-dir-hist-20260929
echo "start $(date -u '+%F %T') UTC"; uptime
for i in 1 2 3 4; do git -C "$G" fetch -q origin main && break || sleep $((i*5)); done
for R in hist histw1; do for S in 0 1; do git -C "$G" show origin/main:$A/runs/$R-s$S/source.json | grep -q '"v1_pass": true' || { echo "WAITING: no committed passing source.json for $R seed $S"; exit 5; }; [ -f "$W/$A/runs/$R-s$S/source.pt" ] || { echo "ABORT: source.pt missing in $W"; exit 6; }; done; done
git -C "$G" archive origin/main scripts $A artifacts/claude-fewex-20260927 | tar -x -C "$W" || exit 4
cd "$W" || exit 4
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
mkdir -p $A/eq-runs
ladder() {  # $1 plugin, $2 source run name, $3 seed, $4 out name
  nohup perl -e 'alarm shift; exec @ARGV' 19800 $PY scripts/claude_fewex_eq_bench.py adapt --plugin $1 --arm loop --seed $3 --init pre --source $A/runs/$2-s$3 --out $A/eq-runs/$4 --threads 1 > $A/eq-runs/$4.log 2>&1 &
  echo "$4 pid $!"
}
for S in 0 1; do ladder claude_dir_hist_net hist $S hist-pre-s$S; ladder claude_dir_hist_net_w1 histw1 $S histw1-pre-s$S; done
wait
for N in hist-pre-s0 hist-pre-s1 histw1-pre-s0 histw1-pre-s1; do echo "== $N"; tail -1 $A/eq-runs/$N.log; ls $A/eq-runs/$N/adapt.json; done
$PY scripts/claude_dir_hist_marks.py judge --hist $A/eq-runs --ctrl $A/eq-runs | tee $A/dev-judge.json
shasum -a 256 $A/eq-runs/*/*.pt > $A/eq-runs/checkpoints-dev-sha256.txt 2>/dev/null
for D in $A/eq-runs/*-pre-s?/; do mkdir -p "$G/$D"; cp $D/adapt.json "$G/$D/"; done
cp $A/eq-runs/*.log $A/eq-runs/checkpoints-dev-sha256.txt "$G/$A/eq-runs/"; cp $A/dev-judge.json "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only): wall time per run; the judge output verbatim; 9x9 dev counts per rung (x of 300) for the four runs.
PUSH: artifacts/claude-dir-hist-20260929/dev-judge.json artifacts/claude-dir-hist-20260929/eq-runs   (adapt.json, logs, sha256 list; NOT the .pt files)
