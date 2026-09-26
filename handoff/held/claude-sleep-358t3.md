COMMON RULES (the sleep research thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
STATUS: RELEASED. Ben approved up to $1.60 (Thread manager relay 18:41 UTC 09-26 of Ben's 18:39:52 message cmsg_01FuvegZXjMmeUzStiEFVnEWVCf81aGiBZ8MSRwbKQBw7t, "you can choose to spend money"). READ ALSO artifacts/claude-rsn358t-20260926/ADDENDUM-v3-1-start-now.md.
GPU: rent
BUDGET: $1.60 including re-rents, on the sleep research line of the Director's ledger. Standing cap is <= $4 per job. TIME CAP: 3 h 15 min from the first rental. Label: claude-sleep-358t3. Never destroy an instance this task did not create.
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Follow the Director's current rental gate. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98; at least 40 GB disk. Keep a running total of dph x hours. At $1.45 or at 3 h 10 min: kill running commands by exact PID, copy back what exists, destroy, stop with BUDGET-STOP, and report which runs finished. If it is not running within 6 min, or the log shows no progress for 10 min, destroy and try another host (max 3 rentals). Launch runs detached (nohup/setsid) so they survive SSH closing. Destroy at the end and confirm it is gone. Append a ledger line.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-rsn358t-20260926/RESULTS-v3.md, or a live instance is labelled claude-sleep-358t3.

YOUR TASK: builder for rsn-358t v3 (v2 with the autocast weight cache off). It has two graded single changes against 358i's loop, each tested against 358i's own plain results:
- loop-trm: a TRM-style training schedule;
- loop8: Ben's looped 8-layer net;
- plus report-only loop8-trm.
The sleep research thread wrote and sealed all code. Run it and never edit it. If something breaks, stop and report the exact error; do not patch. Artifacts go in artifacts/claude-rsn358t-20260926/.
READ FIRST (origin/main): artifacts/claude-rsn358t-20260926/PASSMARKS-v3.md (v2 marks plus V0; it explains why v2 has no verdict) and the docstring of scripts/claude_rsn358t3_run.py.
Needs: torch with CUDA and numpy only. No model downloads.
INDEPENDENCE: artifacts/claude-rsn358i-20260926/tests/ is TEST-ONLY. Never open or print an item; the eval command writes counts only. Run each eval exactly once per checkpoint file.
1. On the rental: `git archive origin/main scripts artifacts/claude-rsn358t-20260926 artifacts/claude-rsn358i-20260926/tests`, extract keeping paths.
2. SEAL: `sha256sum -c artifacts/claude-rsn358t-20260926/SEAL-code-v3.sha256.txt` must show all 22 lines OK; otherwise stop. Then run these and check each output:
   - `python -B scripts/claude_rsn358a_envs.py selftest` prints "selftest ok";
   - `python -B scripts/claude_rsn358t3_run.py selftest` prints "selftest ok";
   - `python -B scripts/claude_rsn358t3_run.py check-mask` prints "check-mask ok";
   - `python -B scripts/claude_rsn358t3_run.py audit` prints four "300/300 puzzles show every needed symbol" lines.
   - STAGE 0 GATE: the line starting "loop  free=3 grad=2 cache=False" must end in "0/12"; otherwise stop with FIX-FAILS-ON-CUDA before any training, destroy, report. Other Stage 0 lines are report only.
   - STAGE 0 (report): `python -c "import torch;print(torch.__version__)"` and `python -B scripts/claude_stage0_autocast_grad.py`; paste both outputs whole into RESULTS-v3.md.
   Anything else: stop.
3. PLAIN: do NOT train plain. 358i's plain results exist on origin/main (checked at sealing): `git show origin/main:artifacts/claude-rsn358i-20260926/runs/plain-s$s/tests.json` for s in 1 2 3 4 (your worktree is stale; read them with git show, never from the worktree). If git show fails for a seed, stop and report; do not train a substitute. (358t v2's builder trained all four plain seeds by mistake, which slowed it past its cap.)
4. TRAIN all AT ONCE and log each to W/<R>.log:
   for s in 1 2 3 4: python -B scripts/claude_rsn358t3_run.py train --arm loop-trm --seed $s --out W/loop-trm-s$s ; and the same with --arm loop8 --out W/loop8-s$s
   for s in 1 2: python -B scripts/claude_rsn358t3_run.py train --arm loop8-trm --seed $s --out W/loop8-trm-s$s
   If memory runs out, drop loop8-trm first, then run four at a time.
   After 10 minutes, project the finish from the logs. If it is past the time cap, stop by exact PID in this order:
   (a) loop8-trm, which is report only;
   (b) then seed 4 of both graded arms, reported as TOO-SLOW, which makes the run INCONCLUSIVE.
   Still finish and evaluate the rest.
5. SEAL each final.pt and final-ema.pt BEFORE its eval: append its sha256 (exactly 64 hex characters; check the length) to artifacts/claude-rsn358t-20260926/SEAL-run-v3.sha256.txt.
6. EVAL once per checkpoint file:
   python -B scripts/claude_rsn358t3_run.py eval --ckpt W/R/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/R/tests.json
   python -B scripts/claude_rsn358t3_run.py eval --ckpt W/R/final-ema.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/R/tests-ema.json
   Copy train_log.jsonl, train_summary.json, both tests*.json and the log into artifacts/claude-rsn358t-20260926/runs-v3/<R>/. Force-add them, because artifacts/ is git-ignored.
7. RESULTS-v3.md, verdict first (V0 first: steps_block_nograd per run from train_summary.json, then):
   - Test A (loop-trm) and test B (loop8) are each PASS / FAIL / INCONCLUSIVE, on G0-G3 exactly as PASSMARKS-v2.md defines them. The loop is the raw final.pt; plain is 358i's plain (or the plain trained here).
   - The proved-wrong clause for each test, and G4-G5.
   - A per-seed table of every test for every arm, raw and EMA, with the 4-seed means.
   - Each loop arm right at 1/2/4/8/12/16/24/32/48 rounds and at any round.
   - loop8 at 1 round vs plain.
   - GPU name, minutes per run, dollars, every deviation.
   Append ledger lines (cat >> artifacts/fable-predictions-ledger.md).
8. PUSH: artifacts/claude-rsn358t-20260926/RESULTS-v3.md artifacts/claude-rsn358t-20260926/SEAL-run-v3.sha256.txt artifacts/claude-rsn358t-20260926/runs-v3 artifacts/fable-predictions-ledger.md. Never push weights. Then copy every final.pt/final-ema.pt to the Mac under ~/premonition-models/rsn358t3/, record the sha256 values, and destroy the rental.
