COMMON RULES (the sleep research thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
STATUS: HELD. This moves to handoff/queue/ only after Ben's yes to the spend (sleep research's $2 is nearly used), relayed by the Thread manager.
GPU: rent
BUDGET: $1.30 including re-rents, on the sleep research line of the Director's ledger. Standing cap is <= $4 per job. TIME CAP: 2 h 30 min from the first rental. Label: claude-sleep-358t. Never destroy an instance this task did not create.
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Follow the Director's current rental gate. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98; at least 40 GB disk. Keep a running total of dph x hours. At $1.15 or at 2 h 25 min: kill running commands by exact PID, copy back what exists, destroy, stop with BUDGET-STOP, and report which runs finished. If it is not running within 6 min, or the log shows no progress for 10 min, destroy and try another host (max 3 rentals). Launch runs detached (nohup/setsid) so they survive SSH closing. Destroy at the end and confirm it is gone. Append a ledger line.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-rsn358t-20260926/RESULTS.md, or a live instance is labelled claude-sleep-358t.

YOUR TASK: builder for rsn-358t (358i with ONE change: the loop's training schedule, TRM-style carried state + EMA; 4 seeds, both arms). The sleep research thread wrote and sealed all code; run it, never edit it. If something breaks, stop and report the exact error; do not patch. Artifacts go in artifacts/claude-rsn358t-20260926/.
READ FIRST (origin/main): artifacts/claude-rsn358t-20260926/PASSMARKS.md and the docstring of scripts/claude_rsn358t_run.py.
Needs: torch with CUDA and numpy only. No model downloads.
INDEPENDENCE: artifacts/claude-rsn358i-20260926/tests/ is TEST-ONLY. Never open or print an item; the eval command writes counts only. Run each eval exactly once per checkpoint file.
1. On the rental: `git archive origin/main scripts artifacts/claude-rsn358t-20260926 artifacts/claude-rsn358i-20260926/tests`, and extract it keeping paths.
2. SEAL: `sha256sum -c artifacts/claude-rsn358t-20260926/SEAL-code.sha256.txt` must show all 18 lines OK; otherwise stop. Then run these and check each output:
   - `python -B scripts/claude_rsn358a_envs.py selftest` prints "selftest ok";
   - `python -B scripts/claude_rsn358t_run.py selftest` prints "selftest ok";
   - `python -B scripts/claude_rsn358t_run.py check-mask` prints "check-mask ok";
   - `python -B scripts/claude_rsn358t_run.py audit` prints four "300/300 puzzles show every needed symbol" lines.
   Anything else: stop.
3. TRAIN all eight AT ONCE and log each to W/<R>.log:
   for s in 1 2 3 4: python -B scripts/claude_rsn358t_run.py train --arm loop --seed $s --out W/loop-s$s ; and the same with --arm plain --out W/plain-s$s
   If memory runs out, run four at a time (seeds 1-2 first). After 10 minutes, project the finish from the logs. If that is past the time cap, stop seed 4 (both arms) by exact PID and report TOO-SLOW for it; PASSMARKS then makes the run INCONCLUSIVE, but still finish and evaluate the rest.
4. SEAL each final.pt and final-raw.pt BEFORE its eval: append its sha256 (exactly 64 hex characters; check the length) to artifacts/claude-rsn358t-20260926/SEAL-run.sha256.txt.
5. EVAL once per checkpoint file, 16 evals:
   python -B scripts/claude_rsn358t_run.py eval --ckpt W/R/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/R/tests-ema.json
   python -B scripts/claude_rsn358t_run.py eval --ckpt W/R/final-raw.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/R/tests-raw.json
   Copy train_log.jsonl, train_summary.json, both tests-*.json and the log into artifacts/claude-rsn358t-20260926/runs/<R>/. Force-add them, because artifacts/ is git-ignored.
6. RESULTS.md, verdict first:
   - G0-G5 exactly as PASSMARKS.md defines them: plain for grading = the better 4-seed mean of plain raw and plain EMA per test; loop = loop EMA. Verdict PASS / FAIL / INCONCLUSIVE, plus the proved-wrong clause.
   - A per-seed table of every test for all four weight sets, and the 4-seed means.
   - The loop right at 1/2/4/8/12/16/24/32/48 rounds and at any round.
   - Rows beside 358i where RESULTS.md exists on origin/builder-outbox or origin/main.
   - GPU name, minutes per run, dollars, every deviation.
   Append ledger lines (cat >> artifacts/fable-predictions-ledger.md).
7. PUSH: artifacts/claude-rsn358t-20260926/RESULTS.md artifacts/claude-rsn358t-20260926/SEAL-run.sha256.txt artifacts/claude-rsn358t-20260926/runs artifacts/fable-predictions-ledger.md. Never push weights. Then COPY the eight loop and plain final.pt/final-raw.pt to the Mac under ~/premonition-models/rsn358t/ (for rv-390 and 358b3). Record the sha256 values, then destroy the rental.
