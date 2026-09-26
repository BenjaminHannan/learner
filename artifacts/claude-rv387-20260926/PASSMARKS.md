# rv-387 pass marks (thought-memory thread, written 2026-09-26 ~13:45 UTC, before any 358i net exists)

Question: around the small loop reasoner, does going back after a bad guess solve more bigger grids than letting the
loop keep thinking, at the same number of rounds?
Idea: Ben, 09-25 19:28 UTC ("revert to an old one ... and go a different direction"). Agreed with Sleep research
(09-25 19:37, 09-26 12:53 and 13:36 UTC): test time only, its nets untouched, runs on 358i's rental after 358i's own
sealed steps, reported apart from the 3x goal and never counted toward it (search around the net, not skill inside it).
Code: scripts/claude_rv387.py (sealed below). Design and research: design/v3/30-modes/384b-revert-and-retry.md.

## Arms (same grids, same budget of 48 loop rounds per grid, same checker)
- KEEP: the loop runs on; solved if the grid passes 358's check_latin at any round within 48.
- GUESS: at every 8th round where the stop head q < 0.5, the code writes the net's top symbol for one open cell as if it
  were a given (the cell the net is surest about without being sure), and the loop runs on. Never goes back.
- BACK: as GUESS, plus a snapshot (h, page, written cells, q) before each guess; if q at a later check round is below
  the snapshot's q, restore it and write the next candidate there (code keeps the tried one ruled out); a cell with
  every candidate used up goes back one more guess.
One change between neighbours: KEEP -> GUESS (writing guesses), GUESS -> BACK (going back). The check_latin checker reads
no answer key: any complete grid that keeps the givens with every symbol once per row and column passes. Fixed before
any run, not tuned: 48 rounds (358a's test rounds), a check every 8 rounds, cut 0.5 (358's own stop rule), sure = 0.99.

## Nets and grids
- Nets: 358i's four loop nets, W/loop-s1..s4/final.pt on 358i's rental, loaded with 358i's R.load. Plain nets unused.
- Grids (made before any net exists, sealed): tests/grids7.jsonl, 300 7x7 grids, seed 387107 (primary; a size 358 never
  trains on) and tests/grids6.jsonl, 300 6x6 grids, seed 387106 (secondary). 358g's legend format, 358's generator
  (unique solutions). Different seeds from 358's own tests (35821-35823).

## Marks (unit = grid; counts are re-checked from the per-grid rows)
- PASS: on grids7, BACK solves at least 15 more grids than KEEP AND at least 10 more than GUESS, in at least 3 of the 4
  seeds.
- PROVED WRONG: on grids7, BACK solves no more grids than KEEP in at least 3 of the 4 seeds.
- Anything else: no clear result.
- Report only: grids6 with the same comparisons; GUESS vs KEEP; guesses, go-backs and rounds used per arm; q at the end.
- Validity: check-load passes for a net (stepping it here matches its own loop_rounds) or that seed is NOT RUN; each
  checkpoint's sha256 is logged; no grid uses more than 48 rounds (asserted); the seal below checks before the run. If
  fewer than 3 seeds run, the result is NOT RUN.

## Predictions
- P387.1 GUESS solves fewer grids than KEEP on grids7 in most seeds (an unsure net's unchecked guesses are often wrong and
  never undone).
- P387.2 BACK solves more than GUESS in most seeds.
- P387.3 Whether BACK beats KEEP by 15 is open: 358a's loop nets already solved 173-192 of 300 7x7 grids on their own.

## Where it runs
358i's vast rental, as a separate section after 358i's results are pushed; this thread's $2 (Director's ledger); 45-minute
cap for the section. Raw output only (artifacts/claude-rv387-20260926/run/); this thread counts, verifies and reports.
