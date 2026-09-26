You are a research partner. I'm Ben, a high-school senior building a small AI model as a personal project. Last night you gave me three experiments; I ran them plus three of my own, and none passed. I want you to help me understand WHY, and what to do next. You can't see my code, so everything you need is below. Where my framing or my experiments are wrong, say so plainly.

## The project in brief

The model is MiniCPM5-1B (a 1-billion-parameter open model), with its thinking mode off. It sits inside a "brain-like" assistant:
- a **notebook** that holds exact facts the user taught it;
- a **reasoner**;
- a **creative mind**, a generator whose job is to maximise lucky hits;
- **sleep**: when idle, the model trains on what worked.

Everything below comes from small experiments on number puzzles. Nothing here has been tested inside the full assistant. Please keep the two apart.

**Hardware and limits:**
- a laptop-class GPU (RTX 5070 Ti, 16 GB);
- cheap rented RTX 5090s (about $0.50/hour, at most $4 per job);
- no new base models without my say-so;
- text written by Claude can't be used as training data;
- public benchmarks (GSM8K, MMLU, HumanEval, IFEval, BFCL, LoCoMo, LongMemEval) are never trained on.

## The puzzle and the loop

**Puzzle:** use each given number exactly once, with + − × ÷ and brackets, to make a target. Two thirds of puzzles have 3 numbers (1-9) and a target from 5-40. One third have 4 numbers (1-13) and target 24. An exact checker (fractions, brute force) says whether an answer is right. Brute force also proves when no answer exists: 458 of the 1,820 four-card hands can't make 24.

**Loop:**
1. The model gives one greedy answer.
2. If that misses, it makes 30 "blurts" (samples at temperature 1.0 or 1.5, chosen on a separate practice set). A "rule keeper" limits sampling to legal expressions over exactly the given numbers, and the model's own probabilities choose among the legal tokens.
3. The checker keeps the right blurts, called lucky hits. A puzzle the greedy answer missed but a blurt solved is "won".
4. Sleep trains a LoRA adapter (rank 16, alpha 32, attention projections, lr 2e-4, batch 8, 3 epochs) on the model's own correct greedy answers plus one hit per won puzzle.
5. The test uses fresh puzzles that were never practised. Main measures:
   - **coverage:** puzzles with at least one right answer in 30 samples (you recommended this as the headline);
   - **lucky samples:** the total count of right samples.

Every run below had pass marks registered before it ran. A FAIL stays a FAIL; I don't re-run to get over a bar.

## Results that already existed (both PASS)

Sleeping on the model's own lucky hits (W) against sleeping on known answers repeated to the same size (C). Lucky samples out of 30 per fresh puzzle:

| Run | Before | W (2 seeds) | C (2 seeds) | Puzzles with ≥1 hit: before → W / C |
|---|---|---|---|---|
| blurt-3 (66 puzzles, T 1.5) | 63 | 126 / 136 | 85 / 87 | 27 → 38, 38 / 3-4 |
| blurt-3r (67 puzzles, T 1.5, new seeds, GPU) | 59 | 129 / 148 | 59 / 58 | 29 → 40, 43 / 3-4 |

## Last night's six results

### 1. Own hits vs. exact-solver answers (your experiment 1): PROVED WRONG

One change from W: for each won puzzle, the training target was a different correct answer found by the brute-force solver (E), chosen as close in length to the model's hit as possible. The test had 184 fresh puzzles (56 of the requested 240 dropped for overlap), with 3 LoRA seeds.

| Arm | Solved in 30 tries (3 seeds) | Solved on 1st try | Lucky samples |
|---|---|---|---|
| before sleep | 77 | 3 | 167 |
| W, own lucky hits | 112 / 108 / 110 | 8 / 9 / 8 | 287 / 326 / 344 |
| E, solver answers, same puzzles | 123 / 113 / 117 | 12 / 14 / 12 | 429 / 429 / 409 |
| C, known answers repeated | 14 / 12 / 11 | 9 / 7 / 8 | 237 / 238 / 237 |

- The 95% interval (bootstrap over number hands) for W − E is −8.7 to +0.5 points.
- Solver targets were shorter on average: 6.96 characters against 8.13.
- Practice: 20 own right answers and 191 won puzzles, so 211 examples per arm.

### 2. Hindsight relabels (my idea, from Hindsight Experience Replay): PROVED WRONG on its measure

A wrong blurt that makes, say, 22 is a correct answer to "make 22 from these numbers".
- **H** added one such relabelled blurt per practice puzzle (375 of them) to W.
- **W** was padded to the same size by repeating its own examples.
- **P** (placebo) used the same blurts with a WRONG relabelled target (v+1).

The test had 64 fresh puzzles, 30 samples each, with T 1.0 chosen on the practice set. There were 2 seeds.

| Arm (560 examples each) | Lucky samples | Puzzles with ≥1 hit (of 64) | Greedy right |
|---|---|---|---|
| before sleep | 66 | 32 | 1 |
| W, padded by repeats | 219 / 223 | 32 / 35 | 5 / 8 |
| H, + right relabels | 156 / 124 | 41 / 43 | 5 / 3 |
| P, + wrong relabels | 163 / 117 | 46 / 42 | 7 / 1 |

- Here W raised luck without raising coverage. In blurt-3r (T 1.5, W not padded) W raised both.

### 3. Asking the model "solvable?" with one letter (your experiment 2): PROVED WRONG

The model was frozen. There were 120 impossible and 120 solvable four-card hands, in matched pairs that differ by one card.

| Format | Impossible called impossible | Solvable called impossible |
|---|---|---|
| "expression, or the word none" (greedy) | 120 | 120 |
| one letter, A = yes / B = no (next-token scores) | 0 | 0 |
| same, meanings swapped | 0 | 0 |

- It says "yes" on all 240 hands under both mappings, so it follows the meaning, not the letter.
- About 80% of the next-token probability sat on the two letters.

### 4. Teaching "can't" through sleep: PROVED WRONG

Practice was 360 solvable and 40 impossible puzzles. The base model said "none" on ALL 400 practice puzzles, so it got 0 solvable ones right.
- **W** slept on expression hits only.
- **N** = W plus 40 code-verified "none" answers on impossible puzzles.

The test had 71 solvable and 78 impossible puzzles.

| Arm | Impossible → "none" | Solvable → "none" | Lucky samples (solvable) |
|---|---|---|---|
| before | 78 | 71 | 87 |
| W (2 seeds) | 0 / 0 | 0 / 0 | 148 / 184 |
| N (2 seeds) | 78 / 78 | 70 / 71 | 137 / 179 |

- So W erased "none" completely and N kept it everywhere. Neither told the two apart.
- When N said none on a solvable puzzle and was forced to answer, it was right 7 times in each seed.

### 5. A cheap "still solvable?" judge on hidden states (your experiment 3): NOT SHOWN, near miss

**Setup:**
- A partial state is what's left of a 4-card hand after one step (3 values) or two steps (2 values). Its label (can it still make 24) is exact.
- The feature is the frozen 1B's last-token hidden state for the text "Numbers left: 8/3, 3. Target: 24. ... can they still make the target?".
- A logistic head is trained on about 1,900 balanced states, with layer and L2 chosen on a dev set.
- The test has 200 matched pairs from held-out hands: 100 with 3 values and 100 with 2, each a live and a dead state from the same hand.
- States are split so no state is in both training and testing. Only 195 distinct 2-value states can make 24 at all.

**Results:**
- The first attempt was invalid: my plain gradient-descent fitter diverged (loss 8-47), and results changed with the CPU thread count.
- Re-fitted with Newton's method (converged), layer 16 of 24 and L2 = 100 won on dev (dev AUC 0.81).
- Pairs right: 158 / 155 / 153 of 200 over 3 seeds, against 111 / 95 / 95 for a shuffled-label placebo.
- By stage: 71 / 68 / 69 on 3-value pairs (the bar was 70) and 87 / 87 / 84 on 2-value pairs.

### 6. Reframing into easier pieces (my idea): FAIL

The same budget of 30 samples per puzzle is spent two ways, with no training:
- **plain:** 30 blurts at the puzzle itself;
- **reframe:** code writes sub-puzzles that drop one number x (make T−x, T+x, x−T, T/x, T·x, x/T; whole-number targets 1-200). The 30 blurts are spread round-robin over them, and a sub-hit is joined back and checked on the original.

| | Solved (of 79) | 3-number (of 52) | 4-number (of 27) |
|---|---|---|---|
| plain | 39 | 32 | 7 |
| reframe | 46 | 41 | 5 |

The bar was 1.5 × plain overall, and at least plain on 4-number puzzles.

## The problems I'm stuck on

1. **What did sleep actually learn?** Solver answers teach as well as the model's own hits, and repeating known answers collapses coverage (77 → 11-14). What mechanism fits ALL the tables above? For example: sharpening the distribution, learning an output style or length, learning that "new puzzles have answers", or something else. What's the cheapest experiment that tells these apart? Could the shorter solver answers be the whole story?
2. **What is the creative part for, then?** If being self-made adds nothing, is the job of a "creative mind" only to FIND checked answers where no solver exists? Or is there a version where the model's own hits should matter (for example, off-policy vs on-policy, or harder puzzles where no solver exists)? What would show that?
3. **Hindsight.** Right and wrong relabels gave the same luck and the same coverage gain. Why? Is the gain just "more varied targets or prompts", and is there any way hindsight could help a 1B?
4. **Temperature and collapse.** W widened coverage at T 1.5 (blurt-3r) but not at T 1.0 (blurt-4), where it only piled luck onto puzzles it could already hit. Is that likely temperature, the padding, or noise? How should the sampling temperature be chosen for practice and for test?
5. **Knowing when it can't.** The 1B has no usable sense of which hands are solvable, whether asked directly or after sleep with verified "none" examples. How do small models learn calibrated "I can't" or "ask the human"? Is it realistic at 1B, or should "can't" always come from code proof or a separate judge?
   - My plan says to use solvable twins and about 10% impossible items. What exact training mix and measure would you use, given that the base says "none" everywhere?
6. **The judge.** 77-79% on pairs, but only 68-71% on the 3-value states, which is where search needs it. Is a frozen 1B plus a linear head the wrong tool (a tiny model on the numbers themselves, or a fine-tuned head)? Is it worth having at all when code can check exactly?
7. **Reframing.** It helped on 3-number puzzles and hurt on 4-number ones, where the pieces still have 3 numbers and the budget is thinly split. Is there a better way to spend a fixed budget across restatements (for example, by the judge's score, or a bandit), or is reframing a dead end at this size?
8. **Method problems.** Are any of my designs flawed in a way that makes these results untrustworthy? Examples:
   - test sets shrinking from overlap drops (240 → 184);
   - 2 seeds;
   - one run per result;
   - coverage and luck pointing in opposite directions (hindsight).

## What I want from you

- **Diagnosis:** for each of the 8 problems, give your best explanation and the main alternative, and say what result would tell them apart.
- **Next three experiments,** ranked by expected information per GPU-hour. Each must be ONE change from something above, with:
  - pass marks fixed in advance, with exact numbers;
  - a control or placebo arm;
  - the result that would prove it wrong.
- **What to stop doing:** which of my ideas (hindsight, reframing, the judge, teaching "can't" through sleep) should I drop, and why?
- **Reaching the real assistant:** given these results, what should sleep train on when the model starts real tasks like coding, where a checker exists (tests) but no solver? What's the smallest test of that?

Rules for your answer:
- Label every claim **shown** (measured; cite it, from my tables or a paper), **suggested** (argued or indirect) or **untested**.
- Keep the puzzle experiments and the full assistant separate.
- One change per experiment.
- Don't invent citations. If you're unsure a paper exists, say so.
- End with a plain-language summary I can read in two minutes.
