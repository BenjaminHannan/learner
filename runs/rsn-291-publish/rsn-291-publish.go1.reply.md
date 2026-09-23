Verifying the missing 291 file — checking existence and seal.
The file exists locally but is absent from origin/main — now tracing the publish mechanism.
The verification mechanics are clear — now checking the outbox state.
Check passes — seal line OK. Now publishing the file to builder-outbox.
The direct push is blocked by tool policy — checking how previous builders published.
VERDICT: CHECK PASSES, PUSH NOT DONE. `scripts/claude_fix291_glue.py` exists in the worktree (8,831 bytes) and its seal line verifies OK, so the file is genuine and publishable. But I did not push it to `origin/builder-outbox`: this environment hard-denies every `git push*` command at the tool-policy level, so the push step was impossible from here. The file is still missing from both `origin/main` and `origin/builder-outbox`. Director: one push from a shell with push rights completes this (exact recipe at the bottom).

Marks table (integer counts):

| Mark | What was checked | Count |
|---|---|---|
| File exists in worktree (`scripts/claude_fix291_glue.py`, 8,831 bytes, dated Sep 23 04:37) | present | 1 / 1 |
| Seal lines checked (`grep claude_fix291_glue.py SEAL \| shasum -a 256 -c` from repo root) | OK | 1 / 1 |
| Seal lines failing | 0 | 0 |
| Files edited or created by me in the repo | 0 | 0 |
| Model changes / runs / test panels opened, read, tuned on, or quoted | 0 | 0 |
| Files pushed to `origin/builder-outbox` | 0 of 1 (blocked, see deviation) | 0 / 1 |

Every move:
1. `git fetch -q origin main`; read `OPUS-RULES.txt` via `git show origin/main:...` (full rules apply; done first).
2. `uptime` (load ~50) and `df -g /` (12 GiB available, over the 3 GB floor) before any heavy step; no heavy step was needed (no runs).
3. Confirmed `scripts/claude_fix291_glue.py` exists in the worktree and is byte-identical to its seal entry: `shasum -a 256` = `8f48830d…cb8a9`, matching seal line 5 exactly.
4. Ran the seal-line check from the repo root. Reported output, verbatim: `scripts/claude_fix291_glue.py: OK` (exit 0).
5. Confirmed the gap the task describes is real: the file is absent from `origin/main` (`git show` → "exists on disk, but not in 'origin/main'") and absent from freshly fetched `origin/builder-outbox` (tip `d7cb06a`), while the other six `scripts/claude_291_*` / `claude_loop291` files are already there.
6. Attempted the push via plumbing-only commands (temp index in `/tmp`, no checkout, no worktree edits); the call was refused by tool policy (`"git push*" action:"deny"`). No push was made, nothing was forced or retried around the policy.
7. Re-verified I changed nothing: no files created, edited, committed, or pushed; only reads and fetches.

Misses: 1 — the PUSH itself (`scripts/claude_fix291_glue.py` → `origin/builder-outbox`) did not happen. No other misses: 0 missing files, 0 hash mismatches, 0 seal failures.

Deviations: 1 — PUSH listed in the task was not executed, solely because `git push` is denied by this sandbox's tool permissions (not by choice, and not worked around). Everything else followed the brief: additive-only (zero writes), no model changes, no runs, no test-panel contact, no `notebook/` writes, no secrets printed, no checkout/merge/push of `main`.

What it means (plain high-school English): the missing 291 glue file sitting in the worktree is the real deal — its fingerprint matches the sealed fingerprint exactly, so it is safe to publish as-is. The only thing left is the actual upload, which has to happen from somewhere allowed to push.
What it doesn't mean: this says nothing about whether experiment 291 itself is good or bad. I ran zero tests and checked zero model behavior — this was a file-identity check only, not a quality verdict on 291.

Director one-step recipe (from the worktree dir, shell with push rights): the file hashes to `8f48830dbc06bcab364b82f45c64e4bd463b51a775c6b8bd4620a8fe1abcb8a9` (matches seal line 5), is absent from `origin/builder-outbox` (tip `d7cb06a` at fetch time — re-fetch first), and can be added as a single additive commit on top of the re-fetched tip containing only `scripts/claude_fix291_glue.py` with that exact content; then verify with `git ls-tree origin/builder-outbox -- scripts/claude_fix291_glue.py` plus `shasum -a 256 -c` on the seal line after `git archive`.
