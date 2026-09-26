COMMON RULES (the sleep research thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
STATUS: RELEASED. Ben approved the $1.60 cap at 15:19 UTC 09-26 (decision card cmsg_01FuvegZXjMmeUzStiEFVnEWBvHvtXgg6u6j1ukfwdZ7q5, option "Add it ($1.60)"), relayed by the Thread manager.
GPU: rent
BUDGET: $1.60 including re-rents, on the sleep research line of the Director's ledger. Standing cap is <= $4 per job. TIME CAP: 3 h 15 min from the first rental. Label: claude-sleep-358t. Never destroy an instance this task did not create.
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Follow the Director's current rental gate. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98; at least 40 GB disk. Keep a running total of dph x hours. At $1.45 or at 3 h 10 min: kill running commands by exact PID, copy back what exists, destroy, stop with BUDGET-STOP, and report which runs finished. If it is not running within 6 min, or the log shows no progress for 10 min, destroy and try another host (max 3 rentals). Launch runs detached (nohup/setsid) so they survive SSH closing. Destroy at the end and confirm it is gone. Append a ledger line.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-rsn358t-20260926/RESULTS.md, or a live instance is labelled claude-sleep-358t.

YOUR TASK: builder for rsn-358t v2. It has two graded single changes against 358i's loop, each tested against 358i's own plain results:
- loop-trm: a TRM-style training schedule;
- loop8: Ben's looped 8-layer net;
- plus report-only loop8-trm.
The sleep research thread wrote and sealed all code. Run it and never edit it. If something breaks, stop and report the exact error; do not patch. Artifacts go in artifacts/claude-rsn358t-20260926/.
READ FIRST (origin/main): artifacts/claude-rsn358t-20260926/PASSMARKS-v2.md (it replaces PASSMARKS.md) and the docstring of scripts/claude_rsn358t_run.py.
Needs: torch with CUDA and numpy only. No model downloads.
INDEPENDENCE: artifacts/claude-rsn358i-20260926/tests/ is TEST-ONLY. Never open or print an item; the eval command writes counts only. Run each eval exactly once per checkpoint file.
1. On the rental: `git archive origin/main scripts artifacts/claude-rsn358t-20260926 artifacts/claude-rsn358i-20260926/tests`, extract keeping paths.
2. SEAL: `sha256sum -c artifacts/claude-rsn358t-20260926/SEAL-code-v2.sha256.txt` must show all 18 lines OK; otherwise stop. Then run these and check each output:
   - `python -B scripts/claude_rsn358a_envs.py selftest` prints "selftest ok";
   - `python -B scripts/claude_rsn358t_run.py selftest` prints "selftest ok";
   - `python -B scripts/claude_rsn358t_run.py check-mask` prints "check-mask ok";
   - `python -B scripts/claude_rsn358t_run.py audit` prints four "300/300 puzzles show every needed symbol" lines.
   Anything else: stop.
3. PLAIN: for s in 1 2 3 4, check that origin/builder-outbox or origin/main has artifacts/claude-rsn358i-20260926/runs/plain-s$s/tests.json. For each seed that is missing, add `train --arm plain --seed $s --out W/plain-s$s` to step 4. Report which plain seeds came from 358i and which were trained here.
4. TRAIN all AT ONCE and log each to W/<R>.log:
   for s in 1 2 3 4: python -B scripts/claude_rsn358t_run.py train --arm loop-trm --seed $s --out W/loop-trm-s$s ; and the same with --arm loop8 --out W/loop8-s$s
   for s in 1 2: python -B scripts/claude_rsn358t_run.py train --arm loop8-trm --seed $s --out W/loop8-trm-s$s
   If memory runs out, drop loop8-trm first, then run four at a time.
   After 10 minutes, project the finish from the logs. If it is past the time cap, stop by exact PID in this order:
   (a) loop8-trm, which is report only;
   (b) then seed 4 of both graded arms, reported as TOO-SLOW, which makes the run INCONCLUSIVE.
   Still finish and evaluate the rest.
5. SEAL each final.pt and final-ema.pt BEFORE its eval: append its sha256 (exactly 64 hex characters; check the length) to artifacts/claude-rsn358t-20260926/SEAL-run.sha256.txt.
6. EVAL once per checkpoint file:
   python -B scripts/claude_rsn358t_run.py eval --ckpt W/R/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/R/tests.json
   python -B scripts/claude_rsn358t_run.py eval --ckpt W/R/final-ema.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/R/tests-ema.json
   Copy train_log.jsonl, train_summary.json, both tests*.json and the log into artifacts/claude-rsn358t-20260926/runs/<R>/. Force-add them, because artifacts/ is git-ignored.
7. RESULTS.md, verdict first:
   - Test A (loop-trm) and test B (loop8) are each PASS / FAIL / INCONCLUSIVE, on G0-G3 exactly as PASSMARKS-v2.md defines them. The loop is the raw final.pt; plain is 358i's plain (or the plain trained here).
   - The proved-wrong clause for each test, and G4-G5.
   - A per-seed table of every test for every arm, raw and EMA, with the 4-seed means.
   - Each loop arm right at 1/2/4/8/12/16/24/32/48 rounds and at any round.
   - loop8 at 1 round vs plain.
   - GPU name, minutes per run, dollars, every deviation.
   Append ledger lines (cat >> artifacts/fable-predictions-ledger.md).
8. PUSH: artifacts/claude-rsn358t-20260926/RESULTS.md artifacts/claude-rsn358t-20260926/SEAL-run.sha256.txt artifacts/claude-rsn358t-20260926/runs artifacts/fable-predictions-ledger.md. Never push weights. Then copy every final.pt/final-ema.pt to the Mac under ~/premonition-models/rsn358t/, record the sha256 values, and destroy the rental.
