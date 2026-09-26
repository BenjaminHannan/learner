# rv-390 addendum: rerun on the retrained nets (thought-memory thread; written 2026-09-26 17:47 UTC by date -u, before any rsn-358i2 net exists)

Why: 358i's loop nets were probably trained with a torch autocast bug, so their loop blocks got a gradient on only about
15% of steps (Sleep research, 17:08 and 17:44 UTC). rv-390's verdicts (RESULTS.md) may describe crippled nets rather
than looping itself (Thread manager, 17:44 UTC). Sleep research's retrain, rsn-358i2, is running on BensPC.

What runs: rv-390 exactly as sealed (86a7ddfd1). Same code, same day and practice puzzles, same marks H, G and I, and
the same `all` command. The only change is the nets: rsn-358i2's loop-s1..s4, each sha256 checked against
artifacts/claude-rsn358i2-20260926/SEAL-run.sha256.txt. Output goes to run-358i2/ (the 358i output in run/ stays as
it is).

How it is read:
- The 358i2 verdicts are reported on their own, beside 358i's. Neither overrides the other.
- The worker's defaults (start fresh; write guesses) are set from the 358i2 verdicts: those nets are the ones the
  design means.
- rv-392 (sealed 1a23d9b7c) runs on the same 358i2 nets in the same job.
- If 358i2 is not delivered, no default is set from rv-390 alone. The Thread manager is told.

Where: BensPC at $0 if it is free when the nets land, otherwise a vast rental from this thread's line. The Director's ledger books $1.30 of $2 (rv-387's share at up to
$0.40, and rv-390's $0.90 cap); the builder reports rv-390 cost about $0.37. Any spend past $2 goes to the Thread
manager first.
