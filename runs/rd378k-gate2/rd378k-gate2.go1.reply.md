Gate task locked — fetching sealed sources and running the 7-turn label check.
No duplicate gate — setting up the sealed run.
Seal check surfaced a mismatch — verifying the exact scope before ruling.
Full seal scope confirmed — compiling the final verdict.
SEAL-MISMATCH — stopped, nothing labelled, nothing copied, nothing pushed.

Counts (integers):
- COMMIT=`81d13ba1c78fa2b5304f341e629300429917b624` (`git log -1 --format=%H origin/main -- artifacts/claude-rd378k-20260926/SEAL-ADD-C.sha256.txt`)
- DUPLICATE gate: 0 files under `artifacts/claude-rd378k-20260926/gate2/` on origin/main; 0 files there on origin/builder-outbox. Not a duplicate.
- SEAL-ADD-C: 2 OK, 0 failed.
- SEAL.sha256: 15 OK, 1 FAILED of 16. Expected 16 OK per task.
- Steps 3-5 run: 0. Teacher API calls: 0. cost_usd: 0. Wall time on label/agree: 0s (not run).
- Files copied into worktree gate2/: 0. `git status --porcelain -- artifacts/claude-rd378k-20260926/gate2/` empty.
- GPU: no. Key: never printed/copied; no `sk-or` in any output checked.

SEAL-ADD-C (`shasum -a 256 -c artifacts/claude-rd378k-20260926/SEAL-ADD-C.sha256.txt`, exit 0), verbatim:
```
artifacts/claude-rd378k-20260926/PASSMARKS-C.md: OK
scripts/claude_rd378k_teacher2.py: OK
```

SEAL (`shasum -a 256 -c artifacts/claude-rd378k-20260926/SEAL.sha256.txt`, exit 1), verbatim, run from tmp extracted at COMMIT plus the sealed JUDGE_NOTES fetched via `git show $COMMIT:<path>` (the task's archive command omits that path; with it present the result is 15 OK + 1 FAILED):
```
artifacts/claude-rd378k-20260926/PASSMARKS.md: OK
scripts/claude_rd378k_data.py: OK
scripts/claude_rd378k_teacher.py: OK
scripts/claude_rd378k_score.py: OK
scripts/claude_rd378_common.py: OK
scripts/claude_rd378_write.py: OK
scripts/claude_rd371b_sample.py: OK
scripts/claude_rd371b_common.py: OK
scripts/claude_lis300_train.py: FAILED
scripts/claude_rd378L_rebuild.py: OK
scripts/claude_rd378u_confirm.py: OK
scripts/claude_rd378L_recall.py: OK
scripts/claude_ep382_store_v2.py: OK
scripts/claude_ep382_store_v3.py: OK
scripts/claude_ep382_store_v4.py: OK
artifacts/claude-rd378-20260925/data/JUDGE_NOTES.md: OK
shasum: WARNING: 1 computed checksum did NOT match
```

Failing line:
- expected (SEAL.sha256.txt at COMMIT): `d9e4b3db4cacc6890ab4fc440a8bfa63739f42455c5114a7ab63f1bbe5ea1f1a  scripts/claude_lis300_train.py`
- actual (`scripts/claude_lis300_train.py` at COMMIT 81d13ba): `a6d4843fda254b9b4e2b8f4e3e47822db4b5fb6f456c0167767049726c20576d`
- cause: `scripts/claude_lis300_train.py` was changed by `f99793d78c783120595cc654bdfa6c2f307cc97e` (2026-09-26T17:15:36Z, grad-None logging) after the seal commit `3316b3ba2703a451e8f0c50189da2c723e9f53a6` (2026-09-26T16:50:25Z) and the seal was never re-issued; COMMIT 81d13ba (2026-09-26T17:35:21Z) inherits the stale hash. JUDGE_NOTES.md at COMMIT matches its seal line (`c56a78e5...`).

Per step 2 ("else stop with SEAL-MISMATCH") I stopped: no selftest, no `teacher2 label`, no `teacher agree`, no worktree writes, no push. Tmp dir used: `/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/opencode/rd378k-gate2-C2NWcx` (outside repo).
