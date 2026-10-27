# Standing research 02: a learned stop that works on kinds it never practised, and knowing when it is wrong

Written 2026-09-28 (standing research helper, Sonnet). Nothing here was run. Link tags: **A** = abstract page fetched and read on 09-28; **T** = title page only; **M** = from memory, not opened (publisher pages refused or gave no text). Labels: shown / suggested / untested.

## What is known in the repo (shown, quoted from H12 DESIGN.md section 2 and not recounted by me)
- Stop rule in the ruler: from round 3 on, stop at the first round where stop-probability > 0.5 **and** the last three answers agree (`scripts/claude_fewex_bench.py:76-78`). Otherwise run to the 48-round cap.
- The stop head is trained only on sums and grids, with target "this round's answer is exactly right" (`scripts/claude_fewex_net.py:171-172`). Nothing trains it on mazes (`claude_fewex_bench.py:205`).
- Result: practised loop hits the cap on 300 of 300 mazes at most rungs in seed 0; seed 1 swings 23 to 300 (`RESULTS-EQ.md:76-84,120-128`). The learned-stop read beats a fixed 16-round read by only 0 to 14 of 300, so the dead stop costs time, not accuracy.
- H12 (`artifacts/claude-dir-h12-stop-20260928/DESIGN.md`) tests training the stop on mazes while adapting. That uses maze answers as labels.

## The gap this research targets
Ben's wish is a stop that works on a kind the net never practised, without needing the new kind's answers. The exactness target needs a right answer, so it cannot be learned from unlabelled problems. Suggested: the fix is a stop target that needs no answer.

## Sources
| source | what it says | tag |
|---|---|---|
| ACT, https://arxiv.org/abs/1603.08983 | Original learned halting for recurrent nets, with a cost on steps. | T |
| PonderNet, https://arxiv.org/abs/2107.05407 | Halting as a learned probability per step, trained end to end. | T (H9 read the abstract) |
| PABEE, https://arxiv.org/abs/2006.04152 | Stop when the answer has not changed for a few steps; no learned head needed. | T (H9 read the abstract) |
| Overthinking / Recall, https://arxiv.org/abs/2202.05826 | Recurrent nets trained on small problems degrade when iterated far ("overthinking"); keeping the problem in view and progressive training fixes it. | A |
| Can you learn an algorithm?, https://arxiv.org/abs/2106.04537 | Recurrent nets trained on easy mazes solve harder ones by thinking longer. | A |
| Path independence, https://arxiv.org/abs/2211.09961 | Nets that reach the same end state from different starts generalise better to harder cases. | A |
| Can you trust your model's uncertainty?, https://arxiv.org/abs/1906.02530 | Large comparison of uncertainty methods under dataset shift. Calibrated confidence is exactly what is needed and shift is when it is worst. I read only the opening; the numeric finding is not quoted here. | A (opening only) |
| Selective classification, https://arxiv.org/abs/1705.08500 | Refuse to answer to hit a chosen error rate, judged by a coverage-versus-risk curve. Gives a ready measuring stick for "knows when it is wrong". | A |
| Language models (mostly) know what they know, https://arxiv.org/abs/2207.05221 | Models can predict whether their own answer is right (P(True), P(IK)). | A (opening only) |
| On calibration of modern nets, https://arxiv.org/abs/1706.04599 | Modern nets are over-confident; one-number temperature fix on held-out data. | T |
| Botvinick et al. 2001, conflict monitoring (anterior cingulate) | Brain signal of competing responses raises caution. | M |
| Kiani and Shadlen 2009, confidence read from the same evidence accumulator that makes the choice | Confidence is not a separate module learned per task; it comes from the state of the decision process. | M |

## Brain angle (suggested, simplified, not checked here)
- Confidence comes from the decision process itself (how much evidence, how much conflict), not from a rule per task. That is why it works on a new task. Our stop reads a head trained against one target on two kinds, which is closer to a per-task rule.
- Silicon can do better: it can run the same problem twice from different starts and compare (R4 in the H9 report), or replay its own last N rounds at no cost.

## Leads, ranked (chance guesses are mine, not measured)
Each is a single change. All three can be run on the existing qualified nets; leads 1 and 3 need no training.

**Lead 1 (guess 55% it beats the current stop's time with no accuracy loss; a diagnostic, not a race entry): a label-free read.** Change only the read rule on the existing practised loop: stop when the answer has stayed identical for N rounds (PABEE), with no stop-head condition, N in {3, 6}. Report cap hits, mean rounds, and right-count against the fixed 16-round read on the same 300 mazes, both seeds, k in 1 to 16,384. Wrong if the label-free read caps as often as today or loses more than the seed-to-seed spread against fixed-16. Caveat: this is a hand-written read, so it is a ceiling and a baseline for Lead 2, not a product piece (goals page, no new hand-written rules). It also shows whether "stable answer" carries any signal on an unpractised kind. Untested.

**Lead 2 (guess 30% that the stop fires before the cap on at least half the mazes at k >= 64 with accuracy within noise of fixed-16; my top learned pick): a stop target that needs no answer.** Change only the stop head's target during the normal sums-and-grids practice: instead of "exactly right now", use "my answer this round equals my answer at round 48" (stability). No labels are needed to build it, so at test time on a new kind the head could even be adapted on unlabelled problems, which is what "works on kinds it never practised" needs. Judge with the ruler's existing rule, nothing else changed. Wrong if, with no maze training of the stop, cap hits stay near 300 of 300, or the head fires but accuracy at the stop falls below fixed-16 by more than the noise. Risk (suggested): stable is not the same as right; a net can settle on a wrong answer, which is what Lead 3 measures. Untested.

**Lead 3 (guess 65% at least one signal has AUROC of 0.7 or better; diagnostic): does anything say "this maze answer is wrong"?** On the practised loop's mazes, score these against right/wrong with no training: stop probability, gap between top two answers, number of answer flips in the last 10 rounds, size of state movement in the last round, and (needs a second run) disagreement of two runs from different starts. Report AUROC and a coverage-versus-risk table (rejecting 10%, 25%, 50% of mazes, error among those kept). Wrong if every signal is at or below 0.6 AUROC in both seeds. Feeds H12's report-only doubt check and R4. Untested.

## Marks reminders (H8 checklist)
Lead 1 and 3 add no gain claim on F_eq, so no bar is set here; if Lead 2 becomes a race entry it needs the higher-of-two comparator, F_few row and a plain-net row (the plain net has no stop, so compare accuracy only). Bars above the noise (about 10 F_eq; H9).

## Not checked / risks
- Abstracts only. None of these papers tested a stop that transfers to a never-practised kind; that combination is the open part.
- I did not check whether Lead 2's target already exists in some form in the code path for practice (`claude_fewex_net.py:171-172` uses exactness only).
- Whether the round-48 answer is itself right on mazes is unknown to me; Lead 2 uses it only as a stability anchor.
