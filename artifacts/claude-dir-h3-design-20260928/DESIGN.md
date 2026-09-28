# H3: the settle-gate loop (a per-cell "surprise-gated carry") for the design race

Written 2026-09-28 19:17 UTC (`date -u`) by helper H3, before any code of this design has run (the writing box has
no torch) and before any score of it exists. Marks: PASSMARKS.md, same folder. Code: scripts/claude_dir_h3_net.py
(plug-in), claude_dir_h3_selftest.py, claude_dir_h3_practice.py, claude_dir_h3_report.py,
claude_dir_h3_gate_report.py. Claim labels: **shown** (in a file I read), **suggested** (my inference),
**untested** (a prediction nobody has run).

## In plain words
The reasoner is a loop: two shared blocks are used again and again, and each pass ("round") every cell of the
puzzle re-reads the puzzle and updates its own notes. Today every cell throws away its old notes and takes what the
blocks propose, every round, for up to 48 rounds, even after it has already worked out its answer.

H3 adds one small learned dial per cell, per round: **how much of the new proposal to take**. The dial looks at two
things about that one cell only: what is being proposed, and how big a change that proposal would be (a measured
"surprise"). A cell whose notes barely need changing can learn to stay put; a cell that is being handed something
new can learn to update fully. Nothing tells the dial which puzzle kind it is looking at, what round it is, or what
a good answer looks like.

Everything else is the loop, unchanged: same two blocks, same attention, same learned stop and 48-round cap, same
training, same learner, same sleep.

## The mechanism, exactly
```
one round, loop today                     one round, H3
------------------------                  ------------------------------------------
h  = notes from last round                h  = notes from last round
e  = puzzle embedding                     e  = puzzle embedding
prop = LN(blocks(h + e))                  prop = LN(blocks(h + e))            (unchanged)
h_new = prop                              d   = mean_c (prop - h)^2           (how big a change, per cell)
                                          s   = log(d + 0.001)                (measured, no gradient)
                                          g   = sigmoid( w.prop + b + a*s )   (one number per cell, 0..1)
                                          h_new = h + g * (prop - h)          (g=1: the loop; g=0: keep notes)
stop = halt(mean over cells of h_new)     stop = halt(mean over cells of h_new)   (unchanged)
```
Extra weights: w has 256, b 1, a 1 = **258**. Stored total **1,645,984** against the loop's 1,645,726
(+258, +0.016%) and the plain net's 1,619,965 (+1.6%, the same gap as the loop). Both counts are the same number
because H3 keeps no fast weights or memory: persistent coefficients = stored weights. Start: w = 0, a = 0, b = +4,
so g = 0.982 everywhere and the net starts as almost the loop. The gate tensors are created after every loop
tensor, so under the same torch seed the loop part gets exactly the loop's random start (selftest checks it).

Two design choices worth knowing:
- The surprise is the size of the **proposed** change, not the change that happened. So a cell that has frozen
  (g near 0) still sees a large proposal the moment new information reaches it (through attention) and can
  reopen. Quiet does not mean done forever. (Suggested; this is the main way the design could fail: see below.)
- The surprise number is measured and detached: it is a signal, not a path for gradients. That keeps the gate
  from learning to game its own input. (The selftest checks that it is detached.)

## Why it is a real design, and why it is general
- Nothing reads a kind label, a round number, a clock or a hand-written rule. The gate sees one cell's own
  256 numbers and its own change. It works on any token grid of any size (7x7, 9x9, 11x11, sums, Latin grids,
  mazes): it uses nothing about layout, walls, paths or digits.
- Learned stop kept, unmodified: the halt head, the "three unchanged predictions" rule and the 48-round cap are
  the harness's own.
- Size: within 0.02% of the loop, no offsetting cut to the MLP needed.
- Costs almost nothing per round (one 256-to-1 product and a few element-wise ops per cell): under 1% of a
  round's work (suggested; timing check in the selftest).

## Brain first, then silicon
**How the brain does it (simplified textbook science, not checked here).** Cortex does not re-drive every
population equally on every pass. Populations whose input is already predicted go quiet (repetition
suppression, adaptation) and the ones still carrying an error stay active; neuromodulators such as
acetylcholine and noradrenaline turn "how surprising is this" into "how much should this circuit change now".
The visual cortex is also known to keep working on the part of a scene that is not yet settled while the settled
part stays put. H3 is the smallest version of that: a per-cell gain on the update, driven by that cell's own
surprise.
**Where silicon does better.** The brain estimates surprise noisily. Here it is measured exactly, for free, as
the size of the proposed change, and it is fed to the gate as a plain number.

## Why it should help learning a new kind from few examples (all suggested / untested)
1. **Focus of the learning signal (suggested).** When a cell holds still, the error signal to that cell passes
   through the identity path and does not push on the shared blocks. In a few-example run the shared blocks then
   get their push from the cells still working out the answer, not from many already-settled cells. Untested.
2. **No drift past the practised depth (suggested).** Practice runs 1 to 16 rounds; a test can run to 48. A cell
   that has settled and closed its dial reads the same at round 40 as at round 16. **Shown** in the baseline
   (RESULTS-EQ.md): the ordinary loop often runs to the cap (for example 163 of 300 cap hits at k=16,384 seed 0,
   and 300 of 300 at several rungs) and some rungs collapse to 0 of 300 with mean rounds 3.0 (fresh loop seed 1,
   k=1,024). That the loop's drift causes these is only suggested.
3. **A cleaner stop (suggested).** When every cell has settled the state stops changing, so the halt head and the
   "predictions unchanged" test agree more easily. Prediction: fewer cap hits than the loop at the same rungs.
None of these is a measured effect. The honest prior for a change this small is low; see "odds" below.

## Is it novel? (plausible, not established)
Gated recurrent updates are old (GRU-style gates, Highway gates, adaptive halting in Universal Transformers and
PonderNet). What is not, as far as I know, standard: a **per-cell gate whose input is that cell's own measured
change**, sitting inside a weight-tied transformer loop that also keeps a global learned stop, with the surprise
kept out of the gradient. A reviewer could reasonably answer "a gated Universal Transformer". I did not run a
literature search from this box, so the novelty claim is **untested**, and the paper should say "surprise-gated
carry, a small variant of gated recurrence" unless a search finds nothing close. Ben's novelty rule is met only in
the weak sense that it is not a plain or bare looped transformer.

## Harvest re-mark (why this one, and what was wrong with the others)
The harvest (design/research/2026-09-28-reasoner-idea-harvest-r1-r5.md) scored ideas against the old ruler with a
+2 point bar. The real bar is +10 on `F_eq` in both seeds (loop 51.00 / 51.29), plus old-kind gates. Re-marked:
| idea | verdict | reason |
|---|---|---|
| Multi-Period Grid Bank | not chosen | The harvest describes absolute row/column tables. The real loop (claude_fewex_net.py Block) already has separate learned bias values for each **relative** row and column offset from -4 to +4, so reusing tables at periods 3, 6, 9 is mostly already expressible, and 72 parameters cannot plausibly give +10. Its "period" story also leans on the maze lattice, which sits close to maze-specific. |
| Sparse-Hash Episodic Slots | not chosen | Slots are wiped every puzzle, so they are a per-puzzle scratch pad, not memory of earlier examples: no route to few-example gain. The harvest's own first cost guess ($96-150) broke the budget rule. |
| TRN Relay Gate | not chosen (close cousin) | Gates only how much of the puzzle embedding is re-added (+257 weights). Weaker than a gate on the whole carried state; H3 covers its purpose. |
| Theta gate | rejected | An autonomous phase that advances every round is a round counter in disguise, which Ben's rule forbids ("no round-number input"). |
| kWTA Sparse | not chosen | The sparse mixture-of-experts loop just came out NOT PROMOTED (+3.88 / -6.25); sparsity alone has not paid on this ruler. |
| Surprise-Gated Carry (E2-R1-A) | **chosen, made per-cell** | Harvest version used one scalar for the whole state; a per-cell gate can freeze the finished part and keep working on the rest, which is the point. |
Not duplicated: the patch race (correction patches), the sparse loop (already run), the relation-net race.

## What would prove it wrong (written before any run)
- The race rule: `F_eq` not 10 points above the loop in both seeds means NOT PROMOTED; not above the loop in both
  seeds means REJECTED (PASSMARKS.md).
- **Dead gate:** if the mean gate stays above 0.98 (or below 0.05) in every round, the gate never did anything and
  any difference is noise or a broken loop. The mechanism is then not tested at all.
- **Premature freezing (the likeliest real failure):** cells freeze before information arrives, so maze accuracy
  falls at high k or at 11x11. Sign: gate mean drops fast in the first rounds while accuracy is below the loop's.
- **Story checks:** if the gain (if any) appears with no fall in cap hits, the "no drift / cleaner stop" account
  is wrong and only the "focus" account remains.
- Note the noise: the loop itself moves several points between seeds; the sparse test's two seeds disagreed by 10
  points. One seed above +10 and one below means NOT PROMOTED, not a win.

## Odds and cost (suggested)
- Odds of clearing the +10 bar in both seeds: low (my guess a few percent to one in ten). The design costs
  almost nothing to try, so it is worth a run, but a PASS would be a surprise and should be treated with care.
- Compute: CPU, fp32, $0, no rental. Measured nothing here (no torch). Scaling from the sparse test's selftest
  timings (loop practice step about 0.37 s sums, 1.28 s grids; maze batch about 1.7 s): practice about 2.8 hours
  per seed (12,000 steps), the four dev ladders about 3 hours in parallel (the baseline's took 169 minutes with
  eight jobs), holdout under an hour: **about 7 to 8 hours of wall time on 4 cores**, run in four queue jobs
  (queue-h3-1-selftest.md, -2-practice.md, -3-dev.md, and -4-holdout.md after the Director commits the dev records). Untested.
- Not run yet: everything. The code was checked by `python3 -m py_compile` only.
