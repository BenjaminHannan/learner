COMMON RULES (helper H3, Claude, wrote this task on 2026-09-28 19:20 UTC for the Director). You are a build/verification agent; follow handoff/director-briefs/rules.md. Additive only: create new files, never edit an existing one. Fictional names only. Do not run git commit or push (the Director commits). Never read or print keys or auth files. Blind panels and readpanel320 are never opened. Claims never exceed the numbers; report every miss and every deviation; integer counts. Check `uptime` and `df -g /` before heavy steps; stop and report if free disk is under 5 GB. Use at most 4 parallel processes. macOS has no `timeout` command (use perl alarm).
GPU: no (CPU only, fp32; the ruler forbids autocast and TF32). DISK: 2.
WORKDIR: run from the git worktree (the current directory). The job builds a private copy of origin/main in $HOME/premonition-h3 (committed files only) and works there, so a later job on the SAME machine finds the checkpoints. Checkpoints stay there and are never pushed.
LOAD-LIGHT: no (2 threads for about 20 minutes). TIME CAP: 60 minutes. LABEL: h3-selftest.
WHY: artifacts/claude-dir-h3-design-20260928/DESIGN.md and PASSMARKS.md (committed before this job). scripts/claude_dir_h3_net.py and its selftest were written on a box with NO torch and were only syntax-checked (python3 -m py_compile). This job is the first time any of it runs. Nothing is trained for a score; no maze is scored.
STOP RULE: if the selftest fails, report the first traceback verbatim and STOP. Do NOT fix the code and do NOT run jobs 2-4. The Director decides.

```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-h3; mkdir -p "$W"
echo "start $(date -u '+%F %T') UTC; worktree $G; work copy $W"; uptime; df -g / | tail -1
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
git -C "$G" archive origin/main scripts artifacts/claude-dir-h3-design-20260928 artifacts/claude-fewex-20260927 | tar -x -C "$W" || exit 4
cd "$W" || exit 4
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$PY -c "import torch,sys; print('torch', torch.__version__, 'python', sys.version.split()[0])" || { echo "ABORT: no torch"; exit 6; }
grep -q '"verdict": "PASS"' artifacts/claude-fewex-20260927/EQ-DEV-GATE.json || { echo "ABORT: baseline EQ-DEV-GATE is not PASS"; exit 5; }
A=artifacts/claude-dir-h3-design-20260928
$PY scripts/claude_dir_h3_selftest.py --out $A/selftest.json --smoke-steps 200 2>&1 | tee $A/selftest.log
echo "selftest rc=${PIPESTATUS[0]}"
$PY scripts/claude_fewex_eq_bench.py selftest --plugin claude_dir_h3_net --threads 2 2>&1 | tee $A/harness-selftest.log
echo "harness selftest rc=${PIPESTATUS[0]}"
echo "ok-lines: $(grep -c '"selftest": "ok"' $A/selftest.log)"
mkdir -p "$G/$A" && cp $A/selftest.json $A/selftest.log $A/harness-selftest.log "$G/$A/" 2>/dev/null
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only): torch and python versions; every printed selftest line verbatim (budget, same_loop, shapes, gate_init, gate_open_equals_loop, gate_range, surprise_detached, gradients_fresh_init, learner, practice_smoke, timing_cpu), the harness-selftest lines, and the two return codes. From timing_cpu state H3 and loop practice-step seconds so job 2's time cap can be checked.
PUSH: artifacts/claude-dir-h3-design-20260928/selftest.json artifacts/claude-dir-h3-design-20260928/selftest.log artifacts/claude-dir-h3-design-20260928/harness-selftest.log
