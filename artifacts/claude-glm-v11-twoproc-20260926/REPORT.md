# Two-process isolation test: scripts/claude_glm_opencode_v11.py — REPORT

Date: 2026-09-26 (runs 20:14:13–20:15:47 UTC). Host: Mac CPU, no GPU.
Script under test: `scripts/claude_glm_opencode_v11.py`, sha256
`7a067cfba8fd147f342d46ed71449ab3e065c46eee3615a9b263a22da5c708c4` — verified, not edited.
Driver (new file, additive only): `artifacts/claude-glm-v11-twoproc-20260926/worker.py`.
Raw logs: `procA.jsonl`, `procB.jsonl` (4 records each), `procA.stdout`, `procB.stdout`.

## Method

- Baseline `opencode session list -n 1000 --format json` from the worktree root: TOTAL 8, glm11-titled 0.
- Started two separate python processes at the same moment (bash `&` + `wait`, both launched 20:14:13 UTC):
  each ran 4 sequential `call("Reply with only the word <word>")` prompts and, before each call
  and after it, recorded only the count and titles of sessions starting with `glm11-`.
  - Proc A words: zircon, lantern, comet, violin.
  - Proc B words: meadow, puppet, anchor, beacon.
- Python launched per host rules (`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
  `uv run --offline --no-project --python 3.12 ...`). Max 2 parallel worker processes.
  No opencode config/auth/key files read or printed. No TEST-ONLY panels used.
- Host load at start: 1-min 82.12 (above the 60 guideline; this test is network-bound,
  2 processes, ~94 s wall time, so it proceeded; load 131.18 at end). Free disk 52 GB.

## Per-call results (integer counts)

Proc A (4/4 replies returned, each exactly the requested word):

| i | word | before_count | after_count | reply |
|---|--------|--------------|-------------|-------|
| 0 | zircon | 0 | 1 (glm11-403d57013b2643a898778bd89cfb5b66) | zircon |
| 1 | lantern | 1 (glm11-403d57013b2643a898778bd89cfb5b66) | 0 | lantern |
| 2 | comet | 1 (glm11-5570f58f63964a67a1235a828d28d8e0) | 0 | comet |
| 3 | violin | 0 | 0 | violin |

Proc B (4/4 replies returned, each exactly the requested word):

| i | word | before_count | after_count | reply |
|---|--------|--------------|-------------|-------|
| 0 | meadow | 0 | 1 (glm11-005eaf81973849f4a5147da234eee3fa) | meadow |
| 1 | puppet | 1 (glm11-005eaf81973849f4a5147da234eee3fa) | 1 (same) | puppet |
| 2 | anchor | 0 | 1 (glm11-59e313647e8943d9bf42bf779d544208) | anchor |
| 3 | beacon | 1 (glm11-59e313647e8943d9bf42bf779d544208) | 1 (same) | beacon |

Replies returned: 8/8. Errors: 0. Call windows overlapped throughout
(A0 20:14:13–20:14:25 with B0 20:14:13–20:14:39; A1/A2 interleaved with B1/B2/B3; see jsonl timestamps).

## Overlap seen

- Proc A saw a live glm11- session at 3 of its 8 observation points
  (A0-after, A1-before, A2-before). By timestamp each falls inside proc B's call window
  (e.g. A0-after/A1-before at 20:14:26 inside B0's call 20:14:13–20:14:39), and since
  `call()` deletes its own tagged session before returning, a before/after listing can
  never show the lister's own session — every glm11- title seen is the other process's
  live session. A saw 2 distinct other-process titles; both were gone at the end.
- Proc B saw a live glm11- session at 6 of its 8 observation points
  (B0-after, B1-before, B1-after, B2-after, B3-before, B3-after); each falls inside
  proc A's call windows (e.g. B0-after/B1-before at 20:14:41 inside A1's call
  20:14:29–20:14:57). Same argument: all seen titles are proc A's live sessions.
  B saw 2 distinct other-process titles; both were gone at the end.
- Mutual overlap: YES — each process saw the other's live glm11- session at least once.
  Never-overlapped report: not applicable.

## End state

- glm11- sessions remaining: 0 (listed twice after the run: FINAL_GLM11 0, REGLM11 0). No leaks.
- Total session count: before 8, after 9 (re-checked: still 9). before == after: NO (+1).
- The +1 is a non-glm11 session: this test creates only `glm11-<uuid>` sessions and deletes
  exactly its own tag per call (final glm11 count 0 confirms cleanup), and `session list`
  creates nothing. The host is shared (load 82→131 during the run), so the extra session
  comes from concurrent activity by another agent on the Mac, not from this test.

## Pass/fail

- 0 glm11- sessions remain: PASS.
- Every reply returned (8/8): PASS.
- Each process saw the other's live session: PASS (A 3/8 points, B 6/8 points).
- Total session count before == after (8 vs 9): FAIL (+1 non-glm11 session, external).
- OVERALL (strict triple condition): FAIL on the total-count criterion only, with the
  diagnosis above. Isolation properties of v11 (no leak, no cross-delete under overlap,
  correct replies) all PASS.

## Deviations and notes

1. Total-count mismatch 8→9 (+1 non-glm11), attributed to shared-host concurrent activity.
2. Host 1-min load above the 60 guideline for the whole run (82 at start, 131 at end);
   proceeded because the test is network-bound and short (94 s).
3. A1-after observed 0 while B was nominally inside B2's call window — the listing at
   20:14:59 ran before B2's session appeared (session creation lags `run` start by seconds).
   Expected race, not a miss.
4. No pushes/commits made (host rules forbid them); "PUSH" satisfied by this file's presence.
   Disk used by this artifact dir: a few KB (worker + logs + this report).
