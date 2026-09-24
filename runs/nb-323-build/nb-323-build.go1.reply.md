Starting the turn-log build — pulling the shared rules and verified base.
I've got the baseline rules — now mapping the daemon, contract, and scoring setup.
Baseline mapped — now studying how turns, sleep, and the notebook interact.
I see how the daemon wraps turns — now checking the build chain and test harness.
Scoring flow is clear — now checking the 274 run details and timing.
I have the full picture now. Setting up the work plan and probing costs.
Build is fast (~1.3s) and turns are milliseconds. Checking record serialization, then writing the turnlog.
Probes look good — fast builds, serializable records. Writing the turnlog module now.
Core log works across restarts. Verifying crash-repair and tamper paths.
Repair and tamper paths verified. Now writing the marks runner.
Test runner written. Now the design note and sealed passmarks.
Seal is locked before any runs. Starting M1 — the panel run.
Panel seal checks out. Launching the M1 arm run (the long pole).
M1 passes clean — 90/90, per-turn identical to 274. Running M2 now.
M2 passes — 600/600 across restarts and sleeps. Running M4 and M5.
M4 found a real bug: a tamper byte that breaks UTF-8 escapes as raw `UnicodeDecodeError` instead of the log's corruption error. Fixing it in the log module, then resealing and re-running all marks on the final code.
Resealed. Re-running all marks fresh on the final code, starting with M1+M2.
M4 and M5 pass. Now the crash test — 30 SIGKILLs.
All marks pass on the final sealed code. Merging results and writing the report.
Seal holds and no existing files were touched by me. Cleaning up test dirs, then staging the push set.
**Verdict: PASS (M1–M4 hold, M5 report-only).**

Exp nb-323 built a durable, hash-chained turn log on the verified 274 base (worktree 274 file confirmed byte-identical to origin/builder-outbox). One new file, `scripts/claude_nb323_turnlog.py`: `TurnLog323` writes one BEGIN before each turn and one END after the reply exists — full text/reply, fsync + read-back, GENESIS hash chain, torn-tail repair — installed LAST around `loop.turn`, so replies are unchanged and `daemon.log.jsonl` is untouched.

## Marks table (integer counts)

| mark | bar | result |
|---|---|---|
| M1 score identical to 274 | 90/90, 0 overlaps, 0 wrong | 90/90, 0 overlaps, 0 wrong (0 moved + 0 old-sheet hits) |
| M1 replies/stores byte-identical to 274 | every turn | 90/90 per-turn, 78/78 stores, probes identical, all 11 score fields identical |
| M2 exact BEGIN+END, in order, matching turn() | 600/600 | 600/600 (20/20 dialogs) |
| M2 restarts / sleeps / lost records | 40 / 40 / 0 | 40 / 40 (threshold 6) / 0 |
| M3 SIGKILLs | 30 | 30 (5 early, 25 mid-run) |
| M3 returned replies missing an END | 0 | 0 (344/344 have ENDs) |
| M3 duplicate ENDs / failed opens | 0 / 0 | 0 / 0 (30/30 opens ok) |
| M3 interrupted turns listed | report | 24 |
| M4 tampers caught on open | 20/20 | 20/20 |
| M5 per-turn overhead median / max | report | 0.197 ms / 0.904 ms |
| M5 open 10,000-turn log (20,000 lines) | report | 0.071 s |

## Every move, miss, deviation

- **Moves: 0.** No reply, write-count, or store changed vs recorded 274 on any of the 90 panel turns.
- **Misses: 0.**
- **Deviations (3, all in RESULTS.md):** (1) OPUS-RULES.txt absent at the tasked path; followed the restated rules. (2) Seal recomputed once: the first M4 run caught a real bug — a tamper byte breaking UTF-8 raised bare `UnicodeDecodeError` instead of `TurnLog323Corrupt`; fixed minimally (fail closed as corrupt), resealed, and **re-ran every mark fresh on the final sealed code** (pre-fix M1/M2 rows voided, not reported). Seal verifies OK. (3) M1 reused 274's verified run274 comparison arms (proven byte-identical 4/4 in 274 M3) with only the 323 slot arm newly run — same runner, config, panel, scorer.

## Plain English

The agent can now be killed mid-sentence and lose nothing it already said: all 344 answers given during 30 kill tests were on disk, the 24 cut-off turns were listed (not silently lost), and all 600 turns survived 40 restarts + 40 sleeps. Any file edit is caught on open (20/20). Answers are word-for-word unchanged (90/90), and the cost is ~0.2 ms per turn. It does not change replies, the notebook, or `daemon.log.jsonl`.

## Push status (blocked, needs one command)

Committed exactly the 7 listed files as `8caf52860` on `claude/card-experiment-handoff-7c5b27` (additive only; `/tmp/nb323` deleted; pre-existing `M artifacts/fable-predictions-ledger.md` untouched). I could not push: this environment denies `git push*` in the shell. To land it, run: `git push origin claude/card-experiment-handoff-7c5b27:builder-outbox` — note builder-outbox's tip (`e16385274`) shares no history with this branch, so push there only if that ref is the intended outbox drop point; otherwise cherry-pick `8caf52860`.
