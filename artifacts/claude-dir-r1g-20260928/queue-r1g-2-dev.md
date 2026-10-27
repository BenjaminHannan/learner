COMMON RULES (helper R1G, Claude, wrote this task on 2026-09-28 for the Director; adapted from the H3 v2 queue files by helper H10). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. macOS has no `timeout` command (use perl alarm).
STATUS: HELD. The Director releases it (see WAIT). Do not run it while HELD.
GPU: no (CPU only, fp32; the ruler forbids autocast and TF32). DISK: 2.
WORKDIR: run from the git worktree (the current directory). The job builds/uses a private copy of origin/main in $HOME/premonition-r1g (committed files only). Checkpoints stay there and are never pushed.
LOAD-LIGHT: no (four single-thread processes). TIME CAP: 330 minutes. LABEL: r1g-dev. MUST RUN ON THE SAME MACHINE AS queue-r1g-1-practice (it reads $HOME/premonition-r1g/.../runs/r1g-s{0,1}/source.pt). The baseline dev jobs took about 169 minutes (RESULTS-EQ.md); this design should be a little slower (untested).
WAIT: start only if origin/main has artifacts/claude-dir-r1g-20260928/runs/r1g-s{0,1}/source.json with "v1_pass": true and artifacts/claude-fewex-20260927/EQ-DEV-GATE.json says PASS. Otherwise ABORT with WAITING.
WHY: PASSMARKS.md order step 3. The dev ladders of the equal-practice ruler, harness UNEDITED: R1g practised and R1g fresh, seeds 0 and 1 (four runs; each k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384; 2,048 updates per rung; both sleeps). Then the dev table and the credit check (DEV panel only: the k = 1,024 net with the reach features off) and the channel-use numbers. NO CHANGE of any kind is allowed after a dev score is seen. The holdout is NOT touched here. The harness refuses to overwrite a finished run; an interrupted run has no resume: delete that run's folder under eq-runs/ and start it again, and say so. Do not delete the .pt files: jobs 3 needs k64.pt, k1024.pt, k16384.pt.
STOP RULE: any traceback: report the first one verbatim, run nothing else.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-r1g; A=artifacts/claude-dir-r1g-20260928
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
for S in 0 1; do git -C "$G" show origin/main:$A/runs/r1g-s$S/source.json | grep -q '"v1_pass": true' || { echo "WAITING: no committed passing source.json for seed $S"; exit 5; }; done
git -C "$G" show origin/main:artifacts/claude-fewex-20260927/EQ-DEV-GATE.json | grep -q '"verdict": "PASS"' || { echo "WAITING: baseline gate not PASS"; exit 5; }
for S in 0 1; do [ -f "$W/$A/runs/r1g-s$S/source.pt" ] || { echo "ABORT: source.pt seed $S missing in $W (run on the machine that ran job 1)"; exit 6; }; done
git -C "$G" archive origin/main scripts $A artifacts/claude-fewex-20260927 | tar -x -C "$W" || exit 4
cd "$W" || exit 4
(shasum -a 256 -c $A/SEAL.sha256.txt) || { echo "STOP: sealed files differ from SEAL.sha256.txt"; exit 6; }
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
NC=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
mkdir -p $A/eq-runs
ladder() {  # $1 seed, $2 init
  nohup perl -e 'alarm shift; exec @ARGV' 19800 $PY scripts/claude_fewex_eq_bench.py adapt --plugin claude_dir_r1g_net --arm loop --seed $1 --init $2 --source $A/runs/r1g-s$1 --out $A/eq-runs/r1g-$2-s$1 --threads 1 > $A/eq-runs/r1g-$2-s$1.log 2>&1 &
  echo "r1g-$2-s$1 pid $!"
}
for S in 0 1; do for I in pre fresh; do ladder $S $I; done; done
wait
for N in r1g-pre-s0 r1g-pre-s1 r1g-fresh-s0 r1g-fresh-s1; do echo "== $N"; tail -1 $A/eq-runs/$N.log; ls $A/eq-runs/$N/adapt.json; done
$PY scripts/claude_dir_r1g_report.py --split dev --runs $A/eq-runs --loop "artifacts/claude-fewex-20260927/eq-runs/loop-s{seed}-pre" --plain "artifacts/claude-fewex-20260927/eq-runs/plain-s{seed}-pre" --out $A/dev-table.json
for S in 0 1; do $PY scripts/claude_dir_r1g_credit.py --seed $S --run $A/eq-runs/r1g-pre-s$S --source $A/runs/r1g-s$S --out $A/credit --threads 1; done
shasum -a 256 $A/eq-runs/r1g-*-s?/*.pt > $A/eq-runs/checkpoints-dev-sha256.txt
for D in $A/eq-runs/r1g-*-s?/; do mkdir -p "$G/$D"; cp $D/adapt.json "$G/$D/"; done
mkdir -p "$G/$A/credit"; cp $A/credit/*.json "$G/$A/credit/"
cp $A/eq-runs/*.log $A/eq-runs/checkpoints-dev-sha256.txt "$G/$A/eq-runs/"; cp $A/dev-table.json "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only): wall time per run; the dev-table lines per seed (F_eq of R1g, fresh R1g, loop, plain, R1g minus loop, F_few of R1g and of the loop) and the 9x9 dev counts per rung (x of 300); mean rounds and cap hits per rung; the credit lines (dev 9x9 on and off at k = 1,024, drop) and the channel-use lines (mean |mix.weight| after practice and at k = 16,384, gamma). Do NOT judge against PASSMARKS: dev numbers are not a verdict.
PUSH: artifacts/claude-dir-r1g-20260928/dev-table.json artifacts/claude-dir-r1g-20260928/credit artifacts/claude-dir-r1g-20260928/eq-runs (adapt.json, logs, sha256 list; NOT .pt files)
