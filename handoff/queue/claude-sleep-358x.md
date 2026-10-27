COMMON RULES (the sleep research thread, Claude, wrote this task on 2026-09-26). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Report in your final reply: verdict first, integer counts, every deviation.
STATUS: RELEASED. Ben approved up to $0.60 at 15:50 UTC 09-26 (decision card cmsg_01FuvegZXjMmeUzStiEFVnEW1ZcuTEwvWrMr3xypKg1TBi, "Approve"), relayed by the Thread manager. The 358i checkpoints are on the Mac (artifacts/claude-grab358i-20260926/REPORT.md).
GPU: rent
BUDGET: $0.60 including re-rents, on the sleep research line of the Director's ledger. TIME CAP: 1 h 15 min from the first rental. Label: claude-sleep-358x. Never destroy an instance this task did not create.
CREDIT GATE (first): `vastai show user --raw` and report ONLY the balance/credit number. Follow the Director's current rental gate. Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
RENTAL RULES: RTX 5090 first, else 4090; reliability >= 0.98; at least 40 GB disk. Keep a running total of dph x hours. At $0.50 or at 1 h 10 min: kill running commands by exact PID, copy back what exists, destroy, stop with BUDGET-STOP. If it is not running within 6 min, or the log shows no progress for 10 min, destroy and try another host (max 3 rentals). Launch runs detached (nohup/setsid). Destroy at the end and confirm it is gone. Append a ledger line.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-rsn358x-20260926/RESULTS.md, or a live instance is labelled claude-sleep-358x.

YOUR TASK: builder for rsn-358x (does practice on sums/grids/number puzzles carry over to mazes, and more for the loop than for plain?). The sleep research thread wrote and sealed all code. Run it and never edit it. If something breaks, stop and report the exact error; do not patch. Artifacts go in artifacts/claude-rsn358x-20260926/.
READ FIRST (origin/main): artifacts/claude-rsn358x-20260926/PASSMARKS-v2.md (replaces PASSMARKS.md) and the docstring of scripts/claude_rsn358x_run.py.
Needs: torch with CUDA and numpy only. No model downloads.
INDEPENDENCE: artifacts/claude-rsn358m-20260926/tests/ is TEST-ONLY. Never open or print an item; the eval command writes counts only. Run each eval exactly once per final-carry.pt.
1. On the rental: `git archive origin/main scripts artifacts/claude-rsn358x-20260926 artifacts/claude-rsn358m-20260926/tests`, and extract it keeping paths.
2. SEAL: `sha256sum -c artifacts/claude-rsn358x-20260926/SEAL-code-v2.sha256.txt` must show all 14 lines OK. Then check each output:
   - `python -B scripts/claude_rsn358a_envs.py selftest` prints "selftest ok";
   - `python -B scripts/claude_rsn358x_run.py selftest` prints "selftest ok".
   Anything else: stop.
3. SOURCES: copy ~/premonition-models/rsn358i/{loop,plain}-s{1,2,3,4}/final.pt from the Mac to the rental as SRC/<arm>-s<seed>.pt. Check each sha256 on both ends against the matching line in origin/builder-outbox or origin/main artifacts/claude-rsn358i-20260926/SEAL-run.sha256.txt. Any mismatch or missing file: stop, and report which.
4. PRACTISE all 16 AT ONCE, logging each to W/<R>.log:
   for s in 1 2 3 4, for arm in loop plain:
     python -B scripts/claude_rsn358x_run.py carry --arm $arm --init pre --seed $s --ckpt SRC/$arm-s$s.pt --out W/$arm-pre-s$s
     python -B scripts/claude_rsn358x_run.py carry --arm $arm --init fresh --seed $s --out W/$arm-fresh-s$s
   If memory runs out, run 8 at a time (seeds 1-2 first).
5. SEAL each final-carry.pt: append its sha256 (64 hex characters) to artifacts/claude-rsn358x-20260926/SEAL-run.sha256.txt BEFORE its eval.
6. EVAL once each: python -B scripts/claude_rsn358x_run.py eval --ckpt W/R/final-carry.pt --tests artifacts/claude-rsn358m-20260926/tests --out W/R/tests.json
   Copy carry_log.jsonl, carry_summary.json, tests.json and the log into artifacts/claude-rsn358x-20260926/runs/<R>/. Force-add them.
7. RESULTS.md, verdict first:
   - X0-X3 exactly as PASSMARKS-v2.md defines them, and PASS / FAIL / INCONCLUSIVE, plus the proved-wrong clause.
   - Per seed: each net's steps-to-bar (from carry_summary.json) and the ratios X1/X2 use; then the 4-seed means.
   - Steps to 150/200 on 7x7 dev.
   - Test counts for all 16 nets.
   - GPU name, minutes, dollars, every deviation.
   Append ledger lines.
8. PUSH: artifacts/claude-rsn358x-20260926/RESULTS.md artifacts/claude-rsn358x-20260926/SEAL-run.sha256.txt artifacts/claude-rsn358x-20260926/runs artifacts/fable-predictions-ledger.md. Never push weights. Destroy the rental.
