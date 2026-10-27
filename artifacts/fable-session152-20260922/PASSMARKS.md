# Exp 152 PASSMARKS (sealed BEFORE the registered run)

Realistic-user session red team on T-Q (loop149 qrewrite) + T-T (loop139b).

- M1 SESSIONS: `scripts/fable_session152_sessions.py:check()` passes
  (6 sessions x 30 turns = 180 turns; expect mix recorded; known classes
  K144/K146/K147/K148/K150/K151 at most one instance each, K146 as one
  two-turn correction+stale pair; all other turns novel).
- M2 COVERAGE: every session runs on BOTH targets, fresh daemon dir per
  (session, target) under `artifacts/fable-session152-20260922/work/`,
  through the mailbox, exactly one inbox file per turn; all 360 turns
  report reply + statuses + fact_writes (no turn averaged or dropped).
- M3 KNOWN-ONLY: turns tagged `known` are judged but EXCLUDED from the
  novelty count (at most one instance per already-known class).
- M4 HONEST-JUDGE: every non-known turn gets exactly one of
  OK / WRONG / UNHELPFUL / HARNESS-ERROR per the brief's definitions;
  WRONG + UNHELPFUL are grouped into root-cause classes, each with a
  file:line and a one-line proposed single-change fix, ranked by how
  often a normal user would hit the class in a 10-minute chat.
- M5 BUDGET: whole registered invocation < 1500 s wall-clock Mac CPU
  with `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`.
- M6 ADDITIVE: no file outside `scripts/fable_session152_*`,
  `artifacts/fable-session152-20260922/` and
  `design/v3/30-modes/152-user-session-redteam-muse.md` is created or
  edited (ledger append lines excepted); no existing file edited.

Falsified by: any missing turn report, any edited non-owned file, any run
over budget, or any WRONG/UNHELPFUL finding without a file:line cause.
