COMMON RULES (helper H3, Claude, wrote this task on 2026-09-28 19:20 UTC for the Director). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. Use at most 4 parallel processes. macOS has no `timeout` command (use perl alarm).
GPU: no (CPU only, fp32; the ruler forbids autocast and TF32). DISK: 2.
WORKDIR: run from the git worktree (the current directory). The job builds a private copy of origin/main in $HOME/premonition-h3 (committed files only) and works there, so a later job on the SAME machine finds the checkpoints. Checkpoints stay there and are never pushed.
LOAD-LIGHT: no (4 single-thread processes). TIME CAP: 330 minutes. LABEL: h3-dev. MUST RUN ON THE SAME MACHINE AS JOB 2 (it reads $HOME/premonition-h3/.../runs/h3-s{0,1}/source.pt).
WAIT: start only if origin/main has artifacts/claude-dir-h3-design-20260928/runs/h3-s0/source.json and h3-s1/source.json (the Director committed job 2's report) with "v1_pass": true in both, AND artifacts/claude-fewex-20260927/EQ-DEV-GATE.json says PASS. Otherwise ABORT with WAITING.
WHY: PASSMARKS.md step 4. The four dev ladders of the equal-practice ruler with the harness UNEDITED: H3 practised and H3 fresh, seeds 0 and 1 (each: k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384; 2,048 updates per rung; both sleeps). The baseline's dev jobs took about 169 minutes with eight running together (RESULTS-EQ.md); expect about the same (untested). The harness refuses to overwrite a finished run; an interrupted run has no resume: delete that run's folder under eq-runs/ and start it again, and say so.
NO CHANGE of any kind is allowed after a dev score is seen. This job only records dev. The holdout is NOT touched here.
STOP RULE: any traceback: report the first one verbatim, run nothing else.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-h3
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
A=artifacts/claude-dir-h3-design-20260928
for S in 0 1; do git -C "$G" show origin/main:$A/runs/h3-s$S/source.json | grep -q '"v1_pass": true' || { echo "WAITING: no committed passing source.json for seed $S"; exit 5; }; done
git -C "$G" show origin/main:artifacts/claude-fewex-20260927/EQ-DEV-GATE.json | grep -q '"verdict": "PASS"' || { echo "WAITING: baseline gate not PASS"; exit 5; }
[ -f "$W/$A/runs/h3-s0/source.pt" ] && [ -f "$W/$A/runs/h3-s1/source.pt" ] || { echo "ABORT: source.pt missing in $W (run on the machine that ran job 2)"; exit 6; }
git -C "$G" archive origin/main scripts $A artifacts/claude-fewex-20260927 | tar -x -C "$W" || exit 4
cd "$W" || exit 4
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
mkdir -p $A/eq-runs
for S in 0 1; do for I in pre fresh; do
  nohup perl -e 'alarm shift; exec @ARGV' 19800 $PY scripts/claude_fewex_eq_bench.py adapt --plugin claude_dir_h3_net --arm loop --seed $S --init $I --source $A/runs/h3-s$S --out $A/eq-runs/h3-$I-s$S --threads 1 > $A/eq-runs/h3-$I-s$S.log 2>&1 &
  echo "seed $S init $I pid $!"
done; done
wait
for S in 0 1; do for I in pre fresh; do echo "== $I s$S"; tail -1 $A/eq-runs/h3-$I-s$S.log; ls $A/eq-runs/h3-$I-s$S/adapt.json; done; done
$PY scripts/claude_dir_h3_report.py --split dev --h3 $A/eq-runs --loop "artifacts/claude-fewex-20260927/eq-runs/loop-s{seed}-pre" --plain "artifacts/claude-fewex-20260927/eq-runs/plain-s{seed}-pre" --out $A/dev-table.json
for S in 0 1; do for K in 64 16384; do
  $PY scripts/claude_dir_h3_gate_report.py --ckpt $A/eq-runs/h3-pre-s$S/k$K.pt --out $A/eq-runs/gate-k$K-s$S.json --threads 1
done; done
shasum -a 256 $A/eq-runs/h3-*-s*/*.pt > $A/eq-runs/checkpoints-dev-sha256.txt
for D in $A/eq-runs/h3-*-s?/; do mkdir -p "$G/$D"; cp $D/adapt.json "$G/$D/"; done
cp $A/eq-runs/*.log $A/eq-runs/gate-k*.json $A/eq-runs/checkpoints-dev-sha256.txt "$G/$A/eq-runs/"; cp $A/dev-table.json "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only): wall time per run; the two dev-table lines per seed (F_eq of H3, fresh H3, loop, plain, H3 minus loop) and the 9x9 dev counts per rung (x of 300) from dev-table.json; mean rounds and cap hits per rung; the gate_report lines at k=64 and k=16,384 (mean gate; say plainly if dead: above 0.98 or below 0.05 in every round). Do NOT judge against PASSMARKS: dev numbers are not a verdict.
PUSH: artifacts/claude-dir-h3-design-20260928/dev-table.json artifacts/claude-dir-h3-design-20260928/eq-runs   (adapt.json, logs, gate reports, sha256 list; NOT the .pt files)
