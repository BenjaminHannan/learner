# rv-390 pass marks (thought-memory thread; written 2026-09-26 16:30 UTC by date -u, before any 358i net has run this code)

Question: when the loop reasoner leaves a puzzle unfinished, does working on it between messages solve more than
starting over with the same compute? And does writing down guesses while it works add to that? The work must stop at
any moment for a message and resume without changing anything (Ben, 14:49 UTC).
Agreed with Sleep research (13:59 UTC; revised marks sent to it before this seal): this thread owns the worker, Sleep
research the nets; the checked answers go to its night pool for its full-loop test. Code: scripts/claude_rv390.py.

## Changes from the unsealed draft, made after rv-387's verdict and before any rv-390 run
- rv-387 (RESULTS.md there): its go-back never fired on 358i's nets, so a BACK arm here would be GUESS under another
  name. BACK is replaced by GUESS (rv-387's GUESS, unchanged in logic). Going back gets its own test later.
- The headline arm is KEEP alone, not "the best downtime arm", so the headline makes one comparison.
- The marks count only HARD puzzles: unfinished, and no round of the day's 48 was accepted by the checker. Otherwise
  every arm gets the day's near misses for free and the comparison measures the checker, not the work.
- Fixed before any run: the draft's sums rows fed sums puzzles to the net labelled as grids. The worker is now
  written so it can stop after any round (its whole state goes to the CPU and back). Answers are saved with the givens
  kept exactly.

## Setup (fixed)
- Nets: 358i's four loop nets (loop-s1..s4/final.pt from the Mac copy), each sha256 checked against
  artifacts/claude-rsn358i-20260926/SEAL-run.sha256.txt before use. No weights change.
- Day: day/ (seeds 39101-39104; sums6, sums8, grids6, grids7, 300 each; 0 clashes with 358i's test items). Each net
  answers at 48 rounds with 358's own v2 stop rule. Unfinished = the checker rejects that answer. HARD = unfinished and
  no round 1-48 accepted.
- Downtime per unfinished puzzle, 480 rounds of the net, the checker allowed at every round:
  - KEEP: one loop from h = 0.
  - RESTART: 10 loops of 48 rounds from h0 = sigma x noise (fixed noise per puzzle and restart). Sigma is picked from
    0.1, 0.3 and 1.0 by the most solves on practice grids (seeds 39113-39114), per net, before its day run.
  - GUESS: rv-387's GUESS. Every 8th round while the stop head q < 0.5, the code writes the net's top symbol for the
    open cell it is surest about (below 0.99) as a given, and never goes back. Disclosed code parts: the checker, and on
    grids the candidates skip symbols already in the cell's row or column.
  - NOTHING: 0 by definition (report only).
- Validity: selftest per net (practice grids only) shows the worker gives exactly rv-387's GUESS on 30 puzzles, or that
  net is NOT RUN. Every saved answer passes the checker (asserted). If fewer than 3 nets run: NOT RUN.

## Marks (unit = hard grids7 puzzle; per net = per seed)
- H (headline), KEEP vs RESTART:
  - PASS: KEEP solves at least 15 more than RESTART in at least 3 of 4 seeds.
  - PROVED WRONG: KEEP solves no more than RESTART in at least 3 of 4 seeds.
  - Anything else: no clear result.
- G (second), GUESS vs KEEP:
  - PASS: GUESS solves at least 10 more than KEEP in at least 3 of 4 seeds.
  - PROVED WRONG: GUESS solves no more than KEEP in at least 3 of 4 seeds.
  - Anything else: no clear result.
- I (interruptible), per seed on the first 40 unfinished grids7 puzzles, with 5 pauses at fixed rounds; at each pause
  a message is answered (the day pass on another puzzle):
  - PASS: in all 4 seeds, KEEP's every-round predictions and stop values, and all 40 GUESS results, equal the run
    without pauses; every message answer equals that message answered with no worker running; and the longest wait
    (one round plus one pause) is under 1 second.
  - FAIL: anything else.
  - The timing is measured on the rental's GPU; the Mac or BensPC is untested.
- Report only: grids6 with the same comparisons; all unfinished (not only hard) counts; KEEP's solves by round 48 vs
  after; sums6 and sums8 KEEP and RESTART, and GUESS as a transfer row (built on grids, never tuned on sums);
  guesses written; sigma per net; seconds.

## Predictions
- P390.1: H is not a PASS. KEEP beats RESTART in most seeds, but by less than 15 (on the tiny rehearsal net, 480 rounds
  instead of 48 added 5 of 60 grids).
- P390.2: GUESS beats KEEP in at least 3 of 4 seeds (in rv-387 it added 11 to 17 grids at 48 rounds).
- P390.3: I passes (the smoke test waited 0.05 s on a CPU).
- P390.4: on sums, GUESS solves no more than KEEP in most seeds: sums have no row or column structure, and wrong digits
  are never undone.
- Seed 4 (the net that never learned practice grids in 358i) will have the most unfinished grids.

## Where it runs
A vast rental (handoff/queue/rent-rv390.md), from this thread's $2 on the Director's ledger. Raw output only in run/;
this thread counts, verifies and reports. The checked answers (run/*.finds.jsonl) go to Sleep research's night pool.
