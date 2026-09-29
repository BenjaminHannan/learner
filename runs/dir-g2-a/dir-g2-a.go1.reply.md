Rate-limited build — running the frozen G-net check heads exactly as sealed.
No duplicate run in progress — setting up the sealed build.
Seals mostly verified, selftest passed — resolving the last seal files.
Workspace fixed — starting the long feature extraction.
75 minutes with zero progress under extreme load — stopping and cleaning up.
STOPPED — environment overload, no heads trained, no eval run, nothing pushed.

What finished:
- Duplicate gate: empty on both origin/main and origin/builder-outbox for artifacts/claude-dir-g2-check-20260929/runs/ — proceeded.
- Weights (before): 6832f4d655242b7183c77edaa1c39c1bce1304083c7ef79937e75580b8739a5f (s13), c1049a23815ad158105816d64b8b245a418a85792c56ac9b06260d78c99a8c68 (s14) — both match required values.
- Seals, all OK: SEAL-g2 3/3, SEAL-g 5/5, SEAL-code 20/20, SEAL-h2 3/3.
- torch 2.14.0 CPU (selftest tail: "selftest ok (torch 2.14.0 CPU)"). Selftest printed [1] rounds_with_feats ok, [2] checker ok, [3] auc 0.75/0.5 ok, [4] tiny end-to-end ok, ending "selftest ok".
- uptime/df at start: load 258.63 271.80 272.51, disk 102 GB free. At end: load 298.21 314.31 315.04, 102 GB free.
- feats-s13: started 10:00:42 UTC, killed by the 75-min blocking-command timeout with rc set by the shell killer, W/feats-s13.log 0 bytes, no W/feats-s13.pt. No other net started.

Per-net results: none. No train-head JSON lines (dev_auc) exist — train-head never ran for s13 or s14. No tests-s13.json / tests-s14.json — eval ran zero times per net (test items never opened). No verdict or gap computed.

ckpt_sha256_after equals before: 6832f4d6…8739a5f (s13), c1049a23…78c99a8c68 (s14) — weights only read, never written.

Cleanup: scratch /var/.../T/opencode/g2-20260929 removed (ls confirms gone), /tmp helper removed, no feature files ever created, worktree W removed (ls W: no such file). Worktree git status shows only pre-existing staged entries from other agents; I staged, committed, and pushed nothing.

Every deviation:
1. Archive extended beyond the task's list with full artifacts/claude-dir-g-build-20260928 — the listed archive left 2 of 5 SEAL-g lines unverifiable (ADDENDUM-1.md, G-BASELINE.md missing). Read-only fetch; no code touched.
2. A mkdir slip created ./W in the worktree; deleted immediately. No new files remain in the worktree from me.
3. Followed the task over the older common rules where they conflict: OMP/MKL=8 (not 1), 6 GB disk gate (not 3 GB), scratch folder (not worktree).
4. Steps 4b–7 not done: no heads, no SEAL-run.sha256.txt, no eval, no runs/, no RUN-NOTE.md, no push. Stopped after one 75-min feats block produced zero bytes because load rose 258 → 313 with unrelated pond adapt jobs holding the CPU; burning the remaining ~4h40m of the 6h cap was unlikely to finish two ~6M row-round extractions. Suggest retry when load drops, or the Director's ≤$0.30 vast-box approval (same commands).
