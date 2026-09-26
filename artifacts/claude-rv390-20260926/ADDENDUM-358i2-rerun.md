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

Update (18:48 UTC by date -u): Ben (18:42 UTC, relayed by the Thread manager at 18:48) ended new vast rentals unless the Thread manager assigns part of the remaining balance. The rerun therefore runs on BensPC only, as handoff/held/rv390-358i2-pc.md already says. If BensPC is busy, the job waits in the queue. It does not go to a rental.
Correction (18:50 UTC by date -u): Ben (18:47 UTC, relayed by the Thread manager at 18:51) gave one $30 rental pool for the project. The Director counts it, and each new rental needs the Thread manager's OK. The job stays on BensPC. A rental would be asked for only if BensPC cannot run it.

Nets (added 20:06 UTC by date -u, before any run on them): Sleep research reported rsn-358i2 SUSPECT CONFIRMED at 20:07 UTC (recount
c761f8717). With the autocast cache off, the loop learns: 358i's grids7 test gives 186, 241, 173 and 177 of 300. The
four nets' sha256 are in NETS-358i2.sha256.txt in this folder. They were copied from origin/builder-outbox 624bfb13e,
artifacts/claude-rsn358i2-20260926/SEAL-run.sha256.txt, and checked by code against Sleep research's message (equal).
That seal file is not yet on main, so the job checks against this copy. Paths: BensPC
C:/Users/benja/premonition-models/rsn358i2/loop-s1..s4/final.pt (Mac copy ~/premonition-models/rsn358i2/). rv-392
(PASSMARKS "Nets") runs on the same nets. No addendum naming 358i is needed.
Expected effect, fixed now: these nets finish more puzzles in the day pass, so the hard sets will be smaller than
rv-390's 183 to 275. The marks are counts (H needs KEEP >= RESTART + 15; G and rv-392 need +10), and with fewer hard
puzzles they are harder to reach. A no-clear-result is therefore more likely than on 358i. The marks stay as sealed.
