# rv-391 dev 2: a learned critic for going back (thought-memory thread; written 2026-09-26 19:29 UTC by date -u, before any trained-net number)

Why: the Thread manager's OBVIOUS FIX FIRST rule (19:33 UTC relay of Ben's 19:20 message). The textbook fix for going
back inside a search is a learned critic, a value head trained on the states the search itself visits, with outcome
labels. Examples are AlphaZero's value net, the evaluator in Tree of Thoughts, and our own plan 384b's dead-end judge.
It has never been tested on the loop reasoner. rv-388 (c3542bb56) tested a judge trained on other states, and only on
the 1B. rv-391 dev (NOTE-dev-result.md) showed that none of the net's untrained signals mark a wrong guess.
Brain first: the anterior cingulate's error signal and dopamine prediction errors are learned from outcomes. This is
textbook-level, and mapping it onto the net is a guess. Silicon can check every answer exactly, so the labels come from
code.

## Step 1 (this note): an unregistered probe, $0 on Mac CPU
- Code: scripts/claude_rv391_critic.py (sealed below). The loop net stays frozen. The critic is a logistic regression
  on the net's own state after each written guess:
  - the mean of h over the answer cells;
  - the mean of h over the written cells;
  - the stop value q.
- Label: dead = 1 if any written guess differs from the puzzle's one solution, checked by code. It is a bare 0/1 target
  (test-hygiene rule 1). It comes from the text, not a prompt (rule 2).
- Training puzzles are fresh and made by code: critic/train/ with seeds 39311 (7x7) and 39312 (6x6), 1000 each. None
  clashes with 358i's test items, rv-390's day or practice puzzles, or rv-392's day. The check puzzles are rv-390's
  practice sets. No test puzzle is touched (rule 3).
- The settings are fixed in the code and nothing is tuned on practice.
- Nets: 358i's four loop nets (the Mac copy, each sha256 against 358i's SEAL-run), plus r0, an untrained net
  (scripts/claude_rv392_randnet.py --seed 0), as a report-only row.

## Marks (fixed now; unit = practice 7x7 states from the four trained nets)
- GOOD ENOUGH TO USE: the critic's AUC for dead vs live states on p-grids7 has a mean of at least 0.65 over the four
  nets and is above 0.5 in every net. Its mean must also beat the count-only baseline (how many guesses are written) by
  at least 0.05.
- PROVED WRONG: a mean of at most 0.55, or a mean no better than the count-only baseline.
- Anything else: no clear result, and the time slice (W = 16) stays.
- Check: on p-grids6, the same critic and cut must flag a larger share of dead states than of live ones in at least 3 of
  4 nets. If not, it is reported as not holding up.
- Report only: the cut, which flags at most 20% of live TRAINING states, and the shares of practice states it flags;
  the training AUC; and r0's row.

Changed before any trained-net number, and disclosed: on the Thread manager I also proposed that r0 must score at least
0.10 lower. A smoke on the untrained net (40 puzzles per set, scratchpad only) gave r0's critic an AUC of 0.80 on
p-grids7, against 0.70 for count-only. So a critic can learn the page's own clashes even from an untrained net's state.
That is still a learned critic, and it is what going back needs. So r0 is now a report-only row, not a mark. The
question "does it come from what the net learned?" is reported, not required.

## Step 2 (if GOOD ENOUGH TO USE): registered rv-391
- One change from the between-messages worker that rv-392 picks: go back when the critic flags the page. Going back
  restores the page before the latest guess and writes the next candidate.
- It runs against the same worker without going back.
- The critic is retrained inside the job on the nets being tested (rsn-358i2's if they exist).
- It uses fresh test grids, 4 nets, and BensPC ($0).
- Marks and predictions are sealed before any run. Whether a critic head may join the reasoner as a learned part is
  the Thread manager's call, and Ben's if it counts as an architecture change.

## Predictions
- P391c.1: GOOD ENOUGH TO USE (the smoke suggests the page's clashes are learnable).
- P391c.2: r0's critic AUC is within 0.10 of the trained nets' mean.
