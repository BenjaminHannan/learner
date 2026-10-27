# rv-392 pass marks (thought-memory thread; written 2026-09-26 17:46 UTC by date -u, before any rv-392 run)

Question: when the loop reasoner leaves a puzzle unfinished and works on it between messages by starting fresh, does
writing down guesses during each fresh start solve more than fresh starts alone?
Why now: rv-390 (artifacts/claude-rv390-20260926/RESULTS.md). Carrying on was PROVED WRONG against restarting; writing
guesses PASSED against carrying on. rv-390's note, fixed before its result, named this as the next single change.
Brain first (Ben, 16:05 UTC): a person stuck on a wrong approach gets unstuck by a break (a fresh start) or by a new
cue, like pencilling in a guess. This tests whether the two add up. It is textbook-level psychology; mapping it onto
the net is a guess.
Code: scripts/claude_rv392.py (imports rv-390's sealed worker, restarts and day pass unchanged). Sealed below.

## Arms (same day pass, same unfinished puzzles, same checker at every round, 480 rounds per puzzle at most)
- RESTART: rv-390's RESTART unchanged: 10 loops of 48 rounds from h0 = sigma x noise.
- RG: the same 10 loops from the same noise, each on a fresh page, with rv-387's GUESS running inside each loop. Every
  8th round while q < 0.5, it writes the net's surest-but-unsure symbol as a given, and never goes back. Guesses are
  not carried from one loop to the next.
- One change between RESTART and RG: the guesses.
- GUESS480 (report only): rv-390's GUESS, one 480-round loop from h = 0.
- Sigma: rv-390's rule, the most RESTART solves on rv-390's practice grids (seeds 39113-39114), per net. RG uses the
  same sigma.
- Disclosed code parts, as in rv-390: the checker, and on grids the guess candidates skip symbols already in the cell's
  row or column.

## Nets and puzzles
- Nets: rsn-358i2's four loop nets (Sleep research's retrain of 358i with the torch autocast bug fixed), each sha256
  checked against artifacts/claude-rsn358i2-20260926/SEAL-run.sha256.txt. If they do not exist when the job is queued,
  a dated addendum written before the run names 358i's loop nets instead. Every report then carries the
  undertrained-nets caveat.
- Day: day/ (seeds 39203-39204, grids6 and grids7, 300 each). 0 clash with 358i's test items or rv-390's day and
  practice puzzles. HARD = unfinished, and no round of the day's 48 accepted.
- Validity: per net, the selftest (practice grids only) must show guess_from equal to rv-390's worker on 30 puzzles,
  or that net is NOT RUN. Every saved answer passes the checker (asserted). If fewer than 3 nets run: NOT RUN.

## Marks (unit = hard grids7 puzzle; per net = per seed)
- PASS: RG solves at least 10 more than RESTART in at least 3 of 4 seeds.
- PROVED WRONG: RG solves no more than RESTART in at least 3 of 4 seeds.
- Anything else: no clear result.
- Report only:
  - grids6 with the same comparison;
  - GUESS480 against both arms;
  - RG solves in its first loop vs later loops;
  - guesses written;
  - the hard count per net beside every count (Sleep research's note).

## Predictions
- P392.1: PASS. In rv-387 guesses added 11 to 17 grids within 48 rounds, and a restart is 48 rounds.
- P392.2: RG solves at least as many hard grids7 puzzles as GUESS480 in at least 3 of 4 seeds.

## Next, fixed now
- If PASS: the between-messages worker is fresh starts with guesses. Going back is built on top of it, with the trigger
  from rv-391's measurement (artifacts/claude-rv391-20260926/NOTE-dev-plan.md).
- If PROVED WRONG: guesses and fresh starts do not add up. The worker is whichever of RESTART and GUESS480 solved more
  hard puzzles here. The next single change is going back inside that worker.
- Otherwise: the worker is RG, since without PROVED WRONG it beat RESTART in at least 2 of 4 nets. Going back is
  tested next.
