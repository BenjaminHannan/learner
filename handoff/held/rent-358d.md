COMMON RULES (the sleep research thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
GPU: rent
BUDGET: $0.80 for this whole task, re-rents included (the Director's overnight reserve; standing caps <=$4 per job, $30 total). TIME CAP: 1 h 30 min from the first rental. Label: rent-358d.
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Under $3.00: rent nothing, stop with CREDIT-STOP. Re-check before any re-rent. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98. Keep a running total of dph x hours; at $0.70 or at 1 h 25 min, kill running commands by exact PID, copy back what exists, destroy, stop with BUDGET-STOP (report which runs finished). Not running within 6 min or no log progress for 10 min: destroy and try another host (max 3 rentals). Launch runs detached (nohup/setsid) so they survive SSH closing. Destroy at the end and confirm it is gone. Append a ledger line.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-rsn358d-20260926/RESULTS.md, or a live instance is labelled rent-358d. (The BensPC version handoff/held/006j-rsn-358d-train.md is held and must not also run.)

YOUR TASK: builder for rsn-358d (loop reasoner vs plain twin, same as rsn-358a with ONE change: many more 4-number practice puzzles). The sleep research thread wrote and sealed all code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. Artifacts go in artifacts/claude-rsn358d-20260926/.
READ FIRST (origin/main): artifacts/claude-rsn358d-20260926/PASSMARKS.md, artifacts/claude-rsn358a-20260925/PASSMARKS-v2.md, and the docstring of scripts/claude_rsn358d_run.py (same commands/arguments as scripts/claude_rsn358a_run.py).
Needs: torch with CUDA and numpy only. No model downloads.
INDEPENDENCE: artifacts/claude-rsn358a-20260925/tests/ is TEST-ONLY: never open or print an item; the eval command writes counts only. Run each eval exactly once per checkpoint.
1. On the rental: `git archive origin/main scripts artifacts/claude-rsn358d-20260926 artifacts/claude-rsn358a-20260925`, extract keeping paths.
2. SEAL: `sha256sum -c artifacts/claude-rsn358d-20260926/SEAL-code.sha256.txt`: every line OK, else stop. `python -B scripts/claude_rsn358a_envs.py selftest` ("selftest ok") and `python -B scripts/claude_rsn358d_run.py pool` (expect exactly "pool 75972 four-number puzzles over 1520 hands; 300 held-out hands excluded; target-24 puzzles in pool: 1062"; anything else -> stop).
3. TRAIN all four AT ONCE (each is a ~6.4M-weight net, a few GB of GPU memory; check nvidia-smi after they start; if memory runs out, run two at a time, seed 3 first). Each builds the puzzle pool in ~40 s first. Log each to W/<R>.log.
   python -B scripts/claude_rsn358d_run.py train --arm loop  --seed 3 --out W/loop-s3
   python -B scripts/claude_rsn358d_run.py train --arm plain --seed 3 --out W/plain-s3
   python -B scripts/claude_rsn358d_run.py train --arm loop  --seed 4 --out W/loop-s4
   python -B scripts/claude_rsn358d_run.py train --arm plain --seed 4 --out W/plain-s4
   If after 10 minutes of training the logs project past the time cap, keep seed 3 (both arms) and stop seed 4 by exact PID; report TOO-SLOW for seed 4.
4. SEAL each final.pt (sha256, exactly 64 hex characters; check the length) appended to artifacts/claude-rsn358d-20260926/SEAL-run.sha256.txt BEFORE its eval.
5. EVAL once per checkpoint: python -B scripts/claude_rsn358d_run.py eval --ckpt W/R/final.pt --tests artifacts/claude-rsn358a-20260925/tests --out W/R/tests.json
   Copy train_log.jsonl, train_summary.json, tests.json and the log into artifacts/claude-rsn358d-20260926/runs/<R>/ (force-add; artifacts/ is git-ignored).
6. RESULTS.md, verdict first: G0-G3 for both seeds with integer counts and PASS / FAIL / INCONCLUSIVE per PASSMARKS-v2.md; proved-wrong clause; per-seed table of every test (plain, loop own stop, loop - plain); loop right at 1/2/4/8/12/16/24/32/48 rounds and any round; numbers4/numbers5 for both arms called out; GPU name, minutes per run, dollars; every deviation. Append ledger lines (cat >> artifacts/fable-predictions-ledger.md).
Never push weights; the checkpoints may be discarded with the rental after their sha256 is recorded (copy them to the Mac at ~/premonition-models/rsn358d/<run>/ only if `df -g /` shows at least 8 GB free after the copy).
PUSH: artifacts/claude-rsn358d-20260926/RESULTS.md artifacts/claude-rsn358d-20260926/SEAL-run.sha256.txt artifacts/claude-rsn358d-20260926/runs artifacts/fable-predictions-ledger.md
