Previous agent appears to have finished. Verifying independently against a fresh archive.
All steps verified reproducible. Appending a resume-verification section (additive) to RESULTS.md.
**VERDICT: PASS — all 8 steps complete; resumed agent verified everything rather than re-running it. 0 extra Luna calls.**

**Marks (integer counts)**

| Item | Count |
|---|---|
| Seals OK (re-run) | 7 files / 7 OK, 0 fail |
| Selftests (offline, re-run) | 4/4 ok, 0 fail |
| Live codex selftest | 1/1 (already spent; **not** re-run) |
| Seeds | 60 dialogs / 425 turns |
| Wording calls | 60 calls, 60 parsed, 0 failed, 2 batches, 17.5 min |
| rawcheck2 | OK, 60/60 model ok, 0 dup, 0 route-fail |
| kept / dropped | 404 / 21 (sum 425) |
| Dialogs per minute | 3.43 (60 / 17.5) |
| Reproduced byte-identical outputs | 6/6 (seeds, check.json, kept, drops, style.json, rawcheck2 line) |
| Ledger lines added | 0 |
| Temp dirs removed | 2/2 |

**Moves**
1. Inspected pilot7: prior agent had finished steps 1–8; its `tmp.s26f5jEDyZ` already gone.
2. `git fetch -q origin main`; fresh `git archive` of the 5 required paths into a new temp dir; all 7 seal files verified OK, incl. `PASSMARKS.sha256.txt` (PASSMARKS.md untouched).
3. Re-ran the 4 offline selftests from that dir — all ok, EXIT:0. Deliberately did **not** re-run `claude_luna_codex.py --selftest` (budget is 60 wording + 1 selftest, both already spent).
4. Re-generated seeds (`--seed 327`) → `diff` identical to the published file; re-ran rawcheck2, check_we2, style → all outputs `diff`-identical.
5. Appended section 9 (RESUME VERIFICATION) to RESULTS.md — additive only, no existing line changed.
6. Removed both temp dirs; confirmed gone.

**Misses / deviations**
- **origin/main moved twice during the task** (8e2590aa → 6c86806a → 54167543e). The run's commit stays **8e2590aa8a8b6b4f1ba2ba8388300384b52d2137**. Diff over the 5 required paths touched only `claude_bm398w_data.py`, `claude_brd11.py`, `claude_brd12_dev.py` — none used here — so pilot7's inputs are byte-identical across all three commits.
- No ledger entry added: the ledger has **0** lis320/pilot entries and this task asks for none; the one unstaged ledger line in the worktree is dl-9 (another agent's). Nothing duplicated.
- `artifacts/` is gitignored, so pilot7 sits untracked exactly like pilot6 — left for the watcher to push; I checked out and pushed nothing.
- Earlier agent's own deviation stands: first selftest attempt ran in the worktree cwd and failed 3x, then passed from `$D`.

**What it means:** the GLM→GPT-6 Luna writer swap reproduced the pre-fixed pipeline exactly — 60 clean calls, zero failures, zero route failures, and every published number regenerates from the sealed code. **What it doesn't mean:** nothing is trained, no threshold in ADDENDUM-9 was judged here, and no claim is made beyond these counts.

First 13 lines of `handoff/queue/lis-302-gpu.md` honored: additive only, fictional names only, TEST-ONLY panels never read, reported here. PUSH path `artifacts/claude-lis320-20260926/pilot7` populated (8 files).
