Verifying the missing exp 291 file — checking seal and worktree state.
Found the verification targets — now pinning down how to publish the file.
I've mapped the publish request — now checking how prior pushes reached the outbox.
Check passed — file matches the seal. Now working out the publish step.
The seal comparison needs a closer look — checking what's actually tracked.
VERDICT: CHECK PASSED, PUSH BLOCKED — scripts/claude_fix291_glue.py exists in the worktree and its hash matches the 291 seal, and it is confirmed missing from origin/builder-outbox. I built the exact one-file publish commit locally but could not push it: this sandbox explicitly denies every `git push` command. Nothing was edited, nothing else was pushed.

Check output (from the repo root, as instructed):
- `shasum -a 256 scripts/claude_fix291_glue.py` → `8f48830dbc06bcab364b82f45c64e4bd463b51a775c6b8bd4620a8fe1abcb8a9`, identical to the seal line.
- `grep claude_fix291_glue artifacts/claude-join291-20260923/SEAL.sha256.txt | shasum -a 256 -c -` → `scripts/claude_fix291_glue.py: OK`
- Full seal `shasum -a 256 -c artifacts/claude-join291-20260923/SEAL.sha256.txt` → 11/11 OK (PASSMARKS.md, predicted_moves291.json, loop291-config.json, loop291 agent, fix291 glue, m1, m7run, score, runall.sh, panel.sh, m8.sh).
- `git cat-file -e origin/builder-outbox:scripts/claude_fix291_glue.py` → MISSING (confirmed; the 7 sibling 291 scripts are present, only the glue file is absent, matching the task description).

Marks table (integer counts, this is a publish task — no runs, no model changes):
- Files to verify: 1, found: 1, hash matches: 1, misses: 0
- Seal lines checked: 11, OK: 11, failed: 0
- Ledger predictions duplicated: 0 (P291.1–P291.6 already in artifacts/fable-predictions-ledger.md; none added)
- Existing files edited or deleted: 0
- Files pushed to origin/builder-outbox: 0 (blocked, see below)

Moves (everything I did):
1. Fetched origin main and origin builder-outbox; read OPUS-RULES.txt (applies in full).
2. Checked disk (11 GB free, above the 3 GB stop line) and uptime (load ~72, but no heavy steps were needed — no runs per the brief).
3. Verified the file exists, hash-matches, full seal 11/11 OK, and is missing from builder-outbox.
4. Built publish commit e7d1506407de2d7e504cc95224725173715aa316 on top of builder-outbox tip 79800d87, adding only scripts/claude_fix291_glue.py (mode 100644, same as its 7 siblings). Re-extracted the file from that commit and re-hashed it: 8f48830d…, the sealed value. No worktree or index files were touched (used a temp index, since deleted).

Misses / deviations:
- DEVIATION (forced, not chosen): the PUSH step could not be executed — `git push` is hard-denied by this environment's tool policy, and OPUS-RULES also says no pushes. So the file is verified and staged as local commit e7d1506 but is NOT on origin/builder-outbox yet.
- No other deviations. No TEST-ONLY panels touched. No secrets printed.

What it means (plain English): the 291 experiment's missing glue file is real, correct, and untampered — its fingerprint matches the sealed record exactly, and all 11 sealed files check out. Anyone can trust this copy.
What it doesn't mean: the job is not finished — the file still needs one push to reach builder-outbox, which has to be done by someone with push permission.

To finish (one command, run from this worktree by Ben or the director): `git push origin e7d1506407de2d7e504cc95224725173715aa316:builder-outbox` — then re-fetch and confirm `git show origin/builder-outbox:scripts/claude_fix291_glue.py | shasum -a 256` prints `8f48830d…`. If the push is rejected as non-fast-forward (the watcher commits often), rebuild the same single-file commit on the new tip and push again.
