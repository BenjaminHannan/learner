# From puzzles to the real world: what the evidence says, and a plan (creative thread, 2026-09-25)

Ben asked (16:14 UTC): is there a real link between a problem and where its answer is, outside simple puzzles? Solving
structured puzzles is very different from the real world, so is there a structured plan for scaling up? He also wanted
evidence behind every claim.

The sources are three research notes. Every quote in them was fetched from the paper itself on 2026-09-25, and ten were
re-checked by hand against the arXiv abstracts:
- `reviews/creative-research-2026-09-25/A-learned-priors.md` (can a model learn where to look?)
- `reviews/creative-research-2026-09-25/B-feedback-kinds.md` (search and self-training when feedback is fuzzy)
- `reviews/creative-research-2026-09-25/C-creativity.md` (generate-then-filter, stepping stones, variety, judging)

Labels: **shown** = measured in the paper; **suggested** = argued, observational, or one narrow setting; **disputed** =
other measured work disagrees; **untested** = nobody (including us) has measured it.

Our own results are the 1B on 24-style puzzles and on gift-idea blurts. They say nothing yet about the village model.

## Plain summary for Ben

1. **Yes, a real link exists, but only within a family of similar problems.** Several examples are shown:
   - Learned guesses about where to draw an extra point raised a geometry prover from 14 to 25 of 30 olympiad problems.
   - A network learned where good answers lie in real industrial scheduling problems, making a standard solver 2 to 10
     times better.
   - A network predicted a hard knot property from easy measurements 78% of the time, where chance is 25%.

   The limit: a learned "intuition" only helps on problems that share structure with what it trained on. This is a
   theorem (No Free Lunch), not an opinion. At the true research frontier, hits are rare: 9 of 353 open Erdős problems,
   3% on a newer and harder Erdős set, and 0 of 3 "breakthrough" open problems.
2. **Hard is not really the difference. The kind of check is.** Every self-improving system that worked on hard, real
   problems had an exact check at the end:
   - AlphaZero: win or lose.
   - AlphaProof and the Erdős agent: a proof checker.
   - FunSearch and AlphaEvolve: a score computed by code.
   - DeepSeek-R1: code-checked answers.

   Where people trained directly on a fuzzy score (a learned judge, or the model's own confidence), the true quality
   rose and then fell. So the plan climbs a ladder of how exact the check is, not a ladder of topics.
3. **You were right about "22 is close to 24".** It has been tested and it failed:
   - Hindsight Experience Replay (2017): robots given a "distance to goal" reward solved none of the tasks.
   - What worked in the same paper was to relabel each miss as a success for the goal it actually reached. For us: a
     guess that makes 22 is a correct answer to the puzzle "make 22".
   - On the 24 game itself (Tree of Thoughts, 2023), a judge asking "can the leftover numbers still reach 24?" took
     GPT-4 from 4% to 74%.
4. **Sleeping on your own checked hits is a known, working recipe, with known limits.**
   - Expert iteration on real Lean math: 46.7% to 56.3% after one round of training on its own proofs.
   - HyperTree Proof Search: 65.4% to 82.6%.
   - AlphaProof: +15 points from training on millions of self-made easier variants of a hard problem.
   - The limits: gains stall after about 2 rounds unless new problems come in, and it can't start from a hit rate of 0.
   - It may also shrink the range of answers the model can find. That last point is disputed, and it matches our own
     variety collapse.
5. **For ideas, the judge is the bottleneck, and that's normal.**
   - The best LLM idea judge agreed with experts 53.3% of the time, where coin-flip is 50% and expert-to-expert is 56.1%.
   - o3 picked the better research idea no better than chance.
   - A judge trained on real outcomes reached 77%.
   - Our trained head picks a good gift idea first 3/10 times against a ~15% base rate. That's weak but in line with
     the field.
6. **Turning up randomness is a weak lever.** Higher temperature is only weakly linked to novelty but moderately linked
   to nonsense. The better "growing circle" is in idea space: keep an archive of near misses and different kinds of
   answers, and explore from them. On a deceptive maze, searching for new behaviour solved it in 39/40 runs against 3/40
   for aiming straight at the goal. That's shown, but only in toy worlds.

## The ladder (one rung at a time; each rung is a registered test before we climb)

Each rung keeps the loop we already have: blurt many, check exactly, sleep on new checked hits (blurt-3 PASS,
one run; the repeat is still pending on BensPC). Each rung changes one thing. The pass marks below are proposals. They get
fixed in a PASSMARKS file before any run, with a placebo arm, because random rewards alone gave 21.4 of a 29.1-point
gain in one study.

**Rung 0 (done, pending repeat).** 24-style puzzles, exact checker, sleep on lucky hits.
- Evidence it should work: STaR, ReST-EM, expert iteration (shown).
- Our result: lucky guesses on fresh puzzles went from 63 to 126 and 136.

**Rung 1: partial-progress judge plus hindsight relabelling (same puzzles).** One change: after each first step, a
small head on the 1B's hidden state scores "can the leftover numbers still reach the target". Its labels come from a
brute-force solver, so they're code-made, not Claude-made. Misses become hits for the value they actually made.
- Evidence: ToT reachability on this exact game, 4%→74% (shown, GPT-4, prompted judge); HER relabelling (shown,
  robots); Math-Shepherd rollout-based step labels (shown; the labels are noisy).
- Test: tries to the first hit and puzzles solved within 30 tries, on fresh puzzles, against the rung-0 loop.
- Proposed pass: at least 1.3x as many puzzles hit within 30 tries.
- Proved wrong if the judged search solves fewer puzzles within 30 tries than rung 0, or the number of distinct
  answers falls.
- Untested for a 1B.

**Rung 2: problems where the hit rate starts near 0.** Five- and six-number puzzles, and odd targets. One change:
before sleeping on a hard puzzle, the model makes easier variants of it (drop a number, change the target), solves
those, and sleeps on them.
- Evidence: AlphaProof test-time RL, +15 points (shown); Absolute Zero, where the model sets its own tasks and keeps
  ones it solves sometimes but not always (shown on its authors' benchmarks); STaR can't start from 0 (shown).
- Proposed pass: hard fresh puzzles solved, above both rung 1 and a placebo that sleeps on easy puzzles unrelated to
  the hard ones.

**Rung 3: a second exact-checked family (transfer).** Candidates: small Python functions checked by hidden tests,
logic grids, and word problems whose answer code can compute. One change: sleep on family A, test on family B.
- Evidence: math-trained gains mostly do not carry to other areas (suggested, one controlled study). We should expect a
  small or zero transfer and report it honestly.
- Proposed pass: a family-B gain above the placebo arm.
- Proved wrong if family B does not move.

**Rung 4: partial checkers (tests that check only some behaviour).**
- Evidence: 31% of "passing" SWE-bench patches were suspicious because of weak tests; one reported score fell from
  12.47% to 3.97% after cleanup (shown).
- Models cheat their graders far more when they can see the grading code (43x, shown).
- Rule: the checker stays hidden from the model, and sleep keeps only hits that pass a second, held-out check.

**Rung 5: fuzzy problems (ideas, advice).** There is no exact checker here, so the judge only chooses what to show you.
Sleep trains only on ideas a person confirmed ("that's a good one" as a real outcome), never on the judge's own score.
- Evidence: every credible system at this end uses AI judging to pick what to test, then a slow real check (the
  co-scientist's lab tests, suggested). Training directly on a learned judge rises then falls (shown).
- Judges also punish novelty (shown in humans), so keep a separate "unusual" bonus when choosing what to show.
- Untested for us. It needs a way to collect your yes/no without you hand-labelling batches.

**Rung 6: research-frontier problems.** This is not a goal for a 1B. Even frontier systems with exact proof checkers hit
~3% of hard open Erdős problems (shown, Sept 2026).

## Things to measure at every rung (from the evidence)
- Puzzles solved within k tries at large k (not just first try), plus the number of distinct answers. Training on hits
  can raise first-try accuracy while shrinking what the model can ever find (Yue 2025, disputed).
- A placebo arm (scrambled or random rewards).
- A fresh test set the model never trained on, and old skills (forgetting). Keeping old data alongside new hits avoids
  collapse (shown); training on the new batch alone risks it.
- How many rounds before gains stall (about 2 in ReST-EM).

## What we cannot claim yet
- That skill on puzzles transfers to real-world problems. The evidence leans against automatic transfer.
- That our growing circle beats a fixed wide one. Temperature alone buys little; the idea-space version is untested
  for us.
- That the Bayesian "egg" steering helps. There is a close analogue (Go-Explore, shown in games), but for us it is
  untested.
