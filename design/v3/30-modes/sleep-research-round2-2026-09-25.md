# Sleep research, round 2 (sleep research thread, 2026-09-25)

Ben (01:0x UTC): "can you do more research in how sleep could help us?" A workflow of 7 agents: 5 researchers
(turning wins into skills, learning rules, not forgetting, thinking depth and the stop token, verified
dreaming and how to measure sleep), one synthesis, one skeptic who checked every citation and repo claim.
Read first: plan 360 (the Fix-sleep thread's nightly program) and round 1, so this only adds new ideas.
Raw files: reviews/sleep-research-round2-2026-09-25/. Nothing was run or trained.
Labels: shown (a paper's result, or checked in our code), suggested (argued), untested (our idea).

## The finding that matters most (shown, I checked it in the code)
**The reasoner physically cannot see a third step yet.** Each step of a question has its own input slot
(`Embed.slot`, scripts/claude_rsn294_core.py:405-420, MAX_HOPS = 3). No training kind ever fills the
third slot: I generated 300 items of every kind; value1, who, yesno, correction, count, compare, before,
after use 1 relation, value2 uses 2, missing uses 1 or 2, and only value3 (never trained) uses 3. So
that slot is still its random starting vector, as large as a word, in every checkpoint so far. The 0/30
on three-step is therefore guaranteed by the input, not only by "never practised". Any "learn 2 steps,
try 3" test, including plan 360's extrapolation arm, is broken until this changes.
**Fix (one change, its own run):** a single shared "step of the chain" embedding plus a small order
signal, instead of one separate slot per step, so step 3 looks like steps 1 and 2. A $0 check first:
compare that slot's size with the trained ones in a Mac checkpoint.

Two more shown facts from the skeptic that void planned designs:
- Relation names get fresh random ids in every puzzle (core.py:308-321). "New kinds of chain" made of
  new relation orders look identical to old ones. Held-out families must differ in things the model
  can see: where a correction sits, a missing row, a many-valued relation, a near-miss, a number or thing.
- Rows have no position signal and are already shuffled, so "reorder the rows" twins do nothing.

## Ranked ideas (after the skeptic's corrections)
0. **Shared step embedding** (above). Prerequisite for every extrapolation test. Recipe (this thread).
1. **Puzzle twins that differ by one fact.** Each practice puzzle comes with code-made twins: a step row
   deleted (answer becomes "I don't know"), a step value changed (answer changes), a near-miss added. A
   lazy trick gets one of each pair wrong and loses reward. Evidence mixed: counterfactual data cut
   shortcut use (Kaushik 1909.12434, shown) but was no better than the same amount of plain data on NLI
   (Huang 2010.04762, shown). First: a $0 probe of distractor settings OUTSIDE the training ranges on a
   Mac checkpoint; then ~$2 twins vs a twin model with the same number of unpaired puzzles, "change a
   value" held out for the panel. Pass: both answers of a pair right +15 points on the blind panel;
   raw (pre-check) invented answers on broken chains at most half the twin's, n >= 60. Wrong: practice
   pairs >= 95% right but blind pairs within 5 points of the twin.
2. **Dose test on visible chain families.** Teach three-step (after fix 0) with 1, 4 or 16 visible
   families and test on families never seen. This is round 1's C1 plus a dose curve; it tells sleep how
   many distinct kinds of win it needs, not how many wins (RFT 2308.01825, shown: gains grow with distinct
   paths). Pass: held-out >= 50% of in-family at 16; wrong: in-family >= 25/30 with held-out <= 5/30.
3. **Practise where it almost fails.** Log the share of practice groups where all 8 tries score the
   same (zero learning signal; run.py:110, shown). If >= 30%, sample puzzles whose success rate is in
   the middle band (2504.03380, DART-Math 2407.13690, shown). $0 count first.
4. **One step per thinking round, then hold** (after rsn-353 passes). The exact solver knows which row
   each step uses; supervise pass t to point at step t's row, and the answer to stay put after the last
   step. Never feed the solver's row back in as input (teacher-forcing hints hurt: Ibarz 2209.11142,
   shown). This also gives the thinking-stop token its label: the first round after which the answer is
   right and stays right.
5. **Thinking longer never hurts** (after rsn-353). Run a random number of rounds without learning,
   then a few with learning, scored only at the end, so the step becomes safe to repeat. Recurrent nets
   trained this way solved much bigger mazes by thinking longer, with no "overthinking" (Bansal
   2202.05826, Anil 2211.09961, shown). Scored at 12 rounds fixed in advance; 48 >= 12 as a second mark.

The stop token itself: trained last, on a frozen network, from "settling" signals only (how much the
state still changes), never from the question's length; gated on more rounds helping by >= 3/30.

## For the nightly sleep cycle (Fix-sleep thread, plan 360)
- **Placebo arm in 363:** the same sleep with grades shuffled. Random rewards "improved" a pretrained
  model on math (2506.10947, shown); the gain vanished on a clean benchmark (2507.10532, shown). Sleep
  only counts if it beats no-sleep, plain extra practice, AND scrambled-grade sleep.
- **363's extrapolation arm is broken until fix 0.** Keep one arm that trains on 1-2 steps and tests on 3,
  but only after the shared step embedding lands. 4-step cannot be encoded at all yet.
- **Self-check 364:** add "both answers of a twin pair right" and "said I don't know although the fact
  was there" as fail lines; the current gate re-asks the day's own questions, which is practice.
- **Wins: count distinct visible families, not wins.** Log practice variety each night to catch the
  STaR-style stall early (B-STaR 2412.17256, shown). Relabelling failed chains (HER) only in the village
  model, capped at 25%; on cards the generator already makes any question.
- **Forgetting:** a $0 multi-night scorecard before 363's multi-night runs; a slow averaged copy of the
  weights as the answering model at commit (free); shrink-and-perturb (Ash & Adams 1910.08475) only if a
  6-night run shows the model stops learning.

## Dropped
Win injection into practice groups on cards (for a one-choice answer it equals plain supervision on the
gold answer); pass@64 (64 tries cover almost every possible answer, so use pass@2 or pass@4); grokking
and very high weight decay (we use fresh data every step, not the small-data setting grokking needs).

## For Ben (plain words)
1. Big find: the model has an input slot for "step 3 of a question" that was never trained, so it could
   never answer a 3-step question, whatever we did in practice. Fix the input first.
2. Then, cheap: practice with puzzle twins that differ by 1 fact, so a lazy trick fails one of each pair.
3. Teach 3 steps with 1, 4 and 16 kinds of chain, and test on kinds it never saw.
4. Once the loop model learns at all, train it so each thinking round does one step, and thinking longer
   never hurts. That also teaches it when to stop.
5. Sleep only counts if it beats no sleep, plain extra practice, and "sleep" with scrambled grades.
