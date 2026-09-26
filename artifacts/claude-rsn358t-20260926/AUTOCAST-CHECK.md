# Autocast check — claude-sleep-358t (2026-09-26)

Owner: Sleep research. Director task 2026-09-26 17:05 UTC. Rent nothing; touched only instance labelled exactly `claude-sleep-358t`.

## Instance
- Label: claude-sleep-358t (exactly one match among 9 running instances)
- Instance id: 52780312
- GPU: 1x RTX 5090, verified, South Korea
- dph_total: 0.4875 (dph_base 0.4667 + disk 0.0208)
- Duration at last reading (pre-destroy): 1614.55 s = 0.4485 h
- Cost: 0.4485 h x $0.4875 = $0.2186 (~$0.22)

## Probe (step 2)
- Rental had no git repo (`git -C ~/job rev-parse` → not a git repository), so the
  `git fetch origin main` step could not run there. Instead the file was taken from
  local `origin/main` (`git show origin/main:scripts/claude_stage0_autocast_grad.py`,
  29 lines) and copied to the rental at /tmp/ag.py, then run from the rental repo
  tree ~/job (cwd required for `scripts/` import). No training, no tests.
- `python -c "import torch;print(torch.__version__)"` → `2.8.0+cu128`
- `python -B /tmp/ag.py` full output (rc=0):
```
torch 2.8.0+cu128 cuda
loop  free=3 grad=2 cache=True : block weight matrices with no gradient 8/12
loop  free=3 grad=2 cache=False: block weight matrices with no gradient 0/12
loop  free=0 grad=2 cache=True : block weight matrices with no gradient 0/12
loop  free=0 grad=2 cache=False: block weight matrices with no gradient 0/12
plain free=0 grad=2 cache=True : block weight matrices with no gradient 0/48
plain free=0 grad=2 cache=False: block weight matrices with no gradient 0/48
```

## Branch taken: STOPPED
- The `cache=True free=3` line shows "no gradient 8/12" (nonzero) → autocast
  cache bug confirmed. All evals skipped per orders.
- Rental training processes listed (`ps -eo pid,etime,cmd | grep -i 358`): 10 PIDs,
  all `python -B scripts/claude_rsn358t_run.py train ...`:
  472, 493, 514, 535, 556, 577, 598, 619, 639, 660.
- Stopped: plain `kill` on all 10 exact PIDs; follow-up `ps` showed none alive,
  so no `kill -9` was needed. PIDs stopped: 472, 493, 514, 535, 556, 577, 598, 619, 639, 660.
- Mac-side builder for claude-sleep-358t stopped by exact PID: 78149 (opencode
  child) via kill; parent wrapper 78114 exited on its own (kill reported no such
  process afterwards). Verified both gone. pythonw 13036 untouched. The
  000-check-358t wrapper (PID 39090) is the check task itself, left running.
- `vastai destroy instance 52780312` executed; re-query by label returns 0 instances → confirmed gone.

## Files copied (counts only)
- Into artifacts/claude-rsn358t-20260926/runs/: 20 files, 121333 bytes total.
  - 10 per-run stdout logs (W/<run>.log), one per run.
  - 10 train_log.jsonl files (W/<run>/train_log.jsonl), one per run.
- No weights copied (run dirs contained only train_log.jsonl; 160K total on rental).
- Line counts of copied train_log.jsonl match rental: 30/28/27/26 (plain-s1..s4),
  20/20/20 (loop-trm-s1..s3), 10/10/10 (loop8-s1..s3).

## Queue (step 4)
- Removed exactly ~/premonition-watch/queue/claude-sleep-358x.pushed (only that file).
  All other queue files untouched.

## Deviations
- OPUS-RULES.txt path from the task (/private/tmp/claude-502/.../OPUS-RULES.txt)
  did not exist; proceeded under the key points restated in the task itself.
- Rental had no git checkout, so origin/main file was sourced locally and shipped over.

Date (UTC): Sat Sep 26 17:08:51 UTC 2026
