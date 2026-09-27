# Proposal (not registered): the lucky-hits idea moved to the reasoner's nights

Creative thread, 2026-09-27 13:43 UTC by `date -u`. For the Thread manager's review and for Sleep research, which
owns the reasoner's nights. Nothing is sealed or coded yet.

## Why
Ben 13:28:08 UTC said "yes" to sleep training only the reasoner, and 13:28:18 "can you make sure that happens all
around". So brd-11 and brd-12 (talker-1B nights) are DO NOT RUN (dd3417cd8), and brd-9's PASS stays a finding.
What carries over from the brd line: a model can get better overnight from answers it FOUND ITSELF and a checker
accepted, where nobody hands it the answer (brd-5..9), and failed tries can be relabelled into checked hits for a
different goal (brd-12's DEV).

## How it differs from Sleep research's nights
- slp-358n/n2 (registered PASS): code supplies every checked answer at night.
- Sleep research's next step (c): reward learning from the reasoner's own right AND wrong tries.
- Proposed here: NO answers from code at night. The reasoner samples several tries per day puzzle it missed; only
  tries the checker accepts become night material (own hits). One extra arm adds hindsight relabelling of wrong tries.
  This is the "puzzles nobody can solve for it" case, the one that matters for new work.

## Draft design (one change per claim)
- Day: the same fresh day puzzles as slp-358n2 (sums and grids of unpractised sizes).
- O (own hits): K sampled tries per missed puzzle; the first checked hit is kept. The night mix is slp-358n2's,
  with own hits in place of code answers.
- H (O + hindsight): a wrong sum a + b = c' becomes the checked example a + (c' − a) = c'; a wrong grid that is
  itself a valid Latin square becomes a checked answer to the puzzle whose givens are its own cells in the given
  positions. The same number of examples as O (matched without repeats), as in brd-12.
- Comparators: N (no night) and C (slp-358n2's code-answer night, the ceiling).
- Claims: O vs N (does self-found material alone improve the reasoner?); H vs O (does relabelling add?). Harm on
  slp-358n2's harm panels, placebo kept.
- CPU, $0 (slp-358n2 took about 20 minutes per seed).

## Open, to settle with Sleep research first
- Does the 358 reasoner's readout allow sampling several different tries (temperature on its answer logits)?
- Does step (c) already include a positive-only (own hits) arm? If so, only H stays here, as an arm of their test.

## Thread manager review (13:44 UTC by `date -u`), to meet before any marks
1. Ownership first: if Sleep research's step (c) has an own-hits arm, H becomes an arm of their plan and they run it;
   otherwise brd-13 runs here with their OK. Never both.
2. No task labels (Ben 11:34): kind-free nets only (358u fixed-env checkpoints, as n3 will use, or in-run nets with
   the env fixed); disclose which.
3. Hindsight rules fixed in code before any run, including which cells become the relabelled grid's givens; report
   how many relabelled items are trivially easy (for example, givens that already fix the square).
4. Marks with a proved-wrong line and the placebo, sent to the Thread manager before sealing.
