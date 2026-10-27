HELD-UNTIL: scripts/claude_dir_lr_lead0.py, artifacts/claude-dir-lr-20260928/LEAD0-MARKS.md are on origin/main (marks precede any run); artifacts/claude-fewex-20260927/runs/qual-loop-s1/source.pt exists on the run machine (it is local, not on main).
GPU: no
LOAD-HEAVY: no (3 one-thread processes, then 3 more; about 45 minutes each batch, my estimate from 169 min per 8 rungs; untested)
WHAT: Lead 0. Re-adapt the practised loop, seed 1, at k = 1,024 and 16,384 with lr 3e-4, 1e-3, 3e-3 (fair ruler, dev 9x9 only, nothing else changed), then the same for the fresh loop, seed 1 (extra, drop it if the queue is tight). Result files are resumable; rerun the same command.
SETUP: torch==2.14.0 CPU, fp32, same as the baseline. Clone origin/main; source nets under artifacts/claude-fewex-20260927/runs/qual-loop-s1/.
RUN (repo root; the six commands of a block can run at once, one thread each):
  for lr in 0.0003 0.001 0.003; do python -B scripts/claude_dir_lr_lead0.py run --arm loop --seed 1 --init pre --lr $lr > artifacts/claude-dir-lr-20260928/lead0-pre-$lr.log 2>&1 & done; wait
  for lr in 0.0003 0.001 0.003; do python -B scripts/claude_dir_lr_lead0.py run --arm loop --seed 1 --init fresh --lr $lr > artifacts/claude-dir-lr-20260928/lead0-fresh-$lr.log 2>&1 & done; wait
AFTER: `python3 -B scripts/claude_dir_lr_lead0.py verdict` (prints counts and the LEAD0-MARKS.md word); commit artifacts/claude-dir-lr-20260928/lead0/*.json and the logs (git add -f).
NOT THIS JOB: any holdout, sleep, or recipe change. Nothing in the marks changes after a score is seen.
