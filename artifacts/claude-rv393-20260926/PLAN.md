# rv-393: pencil marks. Can the reasoner learn to doubt its own guesses? (thought-memory thread; written 2026-09-26 22:42 UTC by date -u; sealed with SEAL.sha256.txt before any real run)

Decided by this thread, under Own your problem. The Thread manager's note at 22:29 UTC said this $0 test does not
need Ben's yes: his yes is reserved for architecture changes (design/v3/30-modes/ben-goals-2026-09-26.md:96) and for
money. The nets here are copies; nothing joins the build. Joining the build would need Ben's yes.
Proposal: artifacts/claude-rv391-20260926/PLAN-own-traces.md. Code: scripts/claude_rv393_pencil.py.

## Why
- Going back needs a signal that says "that guess was wrong". Four tries found none that beats counting guesses:
  - rv-387: the net's "am I done" value never fell.
  - rv-391 dev: none of the net's untrained signals separates wrong guesses from right ones (best mean AUC 0.53).
  - The learned critic on 358i's nets was PROVED WRONG (RESULTS-critic.md).
  - The learned critic on rsn-358i2's nets was PROVED WRONG, 0.763 against counting's 0.794 (RESULTS-critic-358i2.md).
- Root cause (suggested, untested): the rv-390 worker writes each guess as a given. Every given the net ever trained on
  was true, so it trusts whatever is written. Every answer cell it trained on held the blank token
  (scripts/claude_rsn358a_envs.py:191-192), so it has never seen an answer cell that already holds a symbol.

## Brain and field (the mapping is a guess)
- Brain: people learn from their own errors (error-driven learning). They also keep track of which beliefs they
  guessed and which they were told (source monitoring, a frontal-lobe function). This is textbook.
- Silicon: the pencil-or-ink tag here is one exact bit per cell (the slot). Human source memory is error-prone, so
  this is a place where silicon can do better than biology.
- Field: Stream of Search (arXiv 2404.03683) trains a model on search traces that include dead ends, not only on clean
  solutions.

## What runs (per rsn-358i2 loop net, s1 to s4; BensPC, $0; torch with the autocast weight cache off)
1. TRACES. The untouched net runs rv-390's GUESS unchanged: guesses are written as givens, for 96 rounds. It runs on
   the puzzles the 48-round day pass leaves unfinished, out of 4,000 fresh code-made TRAINING 7x7 puzzles (data/,
   seed 39331). None of these puzzles repeats a test, day, practice or critic-training puzzle (data/make-data.json).
   The trace records every guess and the check rounds at which the page held one.
2. FINE-TUNE, two arms. They get the same steps (3,000), batch (128), learning rate (1e-4, 100 warm-up steps, cosine
   to 0), optimizer (358's AdamW), puzzles, rounds and random draws. Half of the steps are 358's usual practice stream.
   The other half replay trace pages: h is carried across page changes, as the worker does, and the last 1 to 6 rounds
   are graded. The loss is 358's: cross-entropy at every answer cell against the true solution, plus 0.5 times the stop
   head's loss. That target is bare and checked by code (hygiene rule 1).
   - PENCIL: each replayed page carries the guesses made so far as pencil marks. The symbol sits in the answer cell,
     and the cell stays an answer cell (slot 1).
   - CLEAN: the same replay with no marks. It controls for the extra 7x7 practice, which the original training never
     had (grids were 4x4 and 5x5 only).
3. MEASURE, for ORIG (the untouched net), PENCIL and CLEAN, in fp32. Each net runs the worker's GUESS rule for 96 rounds
   and never goes back; guesses are written as pencil marks. It runs on the puzzles its own day pass leaves unfinished,
   out of 1,000 fresh PRACTICE 7x7 puzzles (data/pp-grids7, seed 39334).
   - Each mark is judged once, at the first check round after it was written (8 rounds later). It is "overruled" if the
     net's top symbol for that cell, among the puzzle's names, is not the mark.
   - Pages are scored as in rv-391 dev 2: at each check round with at least one mark, before any new guess, a page is
     dead if any mark is wrong. Its score is 1 minus the lowest probability the net gives any of its marks. Count-only
     = the number of marks.
4. NO HARM. Each net is run on 358i's grids6, grids7 and sums6 tests (artifacts/claude-rsn358i-20260926/tests; 358's
   v2 stop rule, 48 rounds). Only the measurement touches these tests; nothing trains on them.

## Marks (unit: the fresh practice set pp-grids7; "a net counts" = at least 30 wrong marks judged in its PENCIL arm)
- VALID only if steps_block_nograd = 0 in all 8 fine-tunes. Otherwise the run shows nothing and is rerun.
- WORKS if both of these hold:
  1. In at least 3 of the 4 nets, the PENCIL arm meets all three of these:
     - it overrules at least 60% of the wrong marks;
     - it overrules at most 10% of the right marks;
     - its wrong-mark overrule rate beats the CLEAN arm's by at least 20 percentage points.
     A net that does not count is a miss here.
  2. Dead-page AUC. The PENCIL arm's mean per-net AUC must beat the mean per-net count-only AUC by at least 0.05, both
     from the PENCIL arm's own states. This is the mean over the 4 nets, the same reading as the critic's mark (the
     Thread manager's question, settled here before any number). The bootstrap range and the pooled count-only AUC are
     reported beside it, as for the critic.
- NO HARM if, for each of grids6, grids7 and sums6, PENCIL minus ORIG, averaged over the nets, is at least -5 of 300.
- PROVED WRONG if any of these holds:
  - the PENCIL arm overrules fewer than 30% of wrong marks in at least 3 of the counted nets;
  - its wrong-mark overrule rate is no higher than CLEAN's in at least 3 of the counted nets;
  - its mean AUC is no better than its mean count-only AUC.
- Otherwise the result is NO CLEAR RESULT.
- If it WORKS but fails NO HARM, the label is WORKS BUT HARMS: it is not usable as is.

## Report-only rows
- ORIG and CLEAN rows on the same measures. If ORIG or CLEAN also meets clause 1's first two thresholds, then pencil
  training is not what did it, and the write-up says so.
- The same measures on rv-390's practice 7x7 (p-grids7, 300 puzzles), which is the critic's set.
- How many unfinished puzzles the no-going-back pencil worker solves (not a test of going back).
- CLEAN's no-harm rows, the train logs, and the trace counts.

## Predictions (fixed now)
- P393.1: WORKS. About 35%.
- P393.2: ORIG overrules fewer than 30% of wrong pencil marks in at least 3 of 4 nets: it trusts what is written,
  even in pencil. About 70%.
- P393.3: CLEAN overrules more wrong marks than ORIG, since the extra 7x7 practice makes it better at 7x7, but less
  than PENCIL. About 50%.

## What would change the plan
- If it WORKS and does no harm, registered rv-391 follows: the worker erases a pencil mark when the net overrules it
  and carries on, against the same worker without erasing. It runs on fresh 7x7 test puzzles with marks sealed first.
  The trigger then comes from the net itself, not from a hand-set time slice.
- If it is PROVED WRONG, the time slice (W = 16) stays the go-back trigger. Going back is then taken to Ben through
  the Thread manager as a brainstorm, per the goals page ("when the ideas run out").

## Deviations and risks, disclosed now
- The traces come from the untouched net writing guesses as givens (the worker as it is). The fine-tuned nets are
  measured writing guesses as pencil marks, so they are not measured on their own traces.
- Replay batches draw with replacement from the traces that have a state at the drawn check round. Late rounds have
  fewer traces, so some batches repeat pages.
- The practice stream uses a fresh seed (net seed + 50), not the original training's draws.
- Time on BensPC is estimated only: 20 to 40 minutes per net, with four nets at once. The cap is 3 hours.
- CPU smoke on an untrained net and fresh dev puzzles (smoke/): it checks the wiring only, and its numbers mean
  nothing.
