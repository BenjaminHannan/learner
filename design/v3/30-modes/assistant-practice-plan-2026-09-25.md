# Practice problems for a real-world assistant, and teaching it to ask (creative thread, 2026-09-25)

Ben (16:37 UTC) asked us to find problems to train on that move toward real-world assistant work, coding
especially, and said the model should learn to ask the human when something really isn't solvable.

The sources are two research notes. In both, licences were read from the Hugging Face API, a dataset card or a repo
LICENSE file, and quotes were fetched from the papers:
- `reviews/creative-research-2026-09-25/D-datasets.md` (practice sets and generators with checkers)
- `reviews/creative-research-2026-09-25/E-asking.md` (abstaining, asking, handing over)

This plan builds on `creative-scaling-plan-2026-09-25.md`, which climbs by how exact the check is. Nothing here is
registered or run yet.

## Practice ladder (easiest first)

| # | Source | Licence | Checker | Why it's here |
|---|---|---|---|---|
| 1 | Reasoning Gym (open-thought/reasoning-gym): 24, countdown, mini sudoku, word ladder, knights-and-knaves, zebra, calendar and time tasks | Apache-2.0 (LICENSE checked) | exact, per-task `score_answer` | Unlimited puzzles with difficulty knobs, so we can start where the hit rate is 30-70%. **Leave out `gsm_symbolic`** (it is built from GSM8K). |
| 2 | Our own small generators: Wordle (multi-turn, exact feedback), unit conversion, JSON extraction | ours | exact | Wordle tests the "update the belief after each guess" idea. The other two are assistant chores. |
| 3 | Lichess/chess-puzzles, mate-in-1 upward by rating | CC0-1.0 (HF API checked) | exact (the solution move line) | Real puzzles people made, with a ready-made difficulty rating. |
| 4 | Function calling: Salesforce xLAM 60k | CC-BY-4.0 | exact match on the function name and arguments | Tool use is core assistant work. Its answers were written by DeepSeek and Mixtral, not Claude. BFCL stays a test set. |
| 5 | Beginner code with tests: MBPP train, APPS introductory, TACO easy | CC-BY-4.0 / MIT / Apache-2.0 (MBPP and TACO checked) | hidden unit tests run in a sandbox | Real coding with human-written solutions. HumanEval stays a test set. |
| 6 | Harder code: TACO medium, CodeContests (and its + version) sorted by rating, rStar-Coder seed problems | CC-BY-4.0 / Apache-2.0 | tests | The ladder continues. rStar-Coder's solutions come from QwQ-32B, so they are not Claude-written. |
| 7 | SQL: Spider train | CC-BY-SA-4.0 | run the query and compare the result | Real database questions with human-written SQL. |
| 8 | Later: SWE-Gym (real GitHub issues) | MIT | repo tests | Almost never solvable by a 1B. Kept as the far rung. |

**Excluded:**
- **NYT Connections sets:** NYT owns the puzzles.
- **Crossword clues:** no English set with a clear training licence.
- **Non-commercial sets (Enigmata-Data, KodCode, APIGen-MT):** we can make our own data with the Apache-licensed Enigmata generator code instead.
- **Sets with no licence:** sudoku-extreme full set, PrimeIntellect verifiable coding, a Countdown set.
- **allenai RLVR-IFeval and IF_multi_constraints:** they contain 140 and 2,133 GSM8K train questions word for word, and they use IFEval's constraint types, which is a test set of ours.
- **SWE-smith and R2E-Gym trajectories:** possibly Claude-written.

## Teaching it to ask (evidence first)

- **Training on its own hits erases "I don't know".** Standard reinforcement fine-tuning cut refusal on unanswerable
  maths by more than 80%. Mixing in 10% unanswerable problems restored it (Hallucination Tax, arXiv 2505.13988,
  shown). Reasoning fine-tuning lowered abstention by 24% on average (AbstentionBench, arXiv 2506.09038, shown).
  Our sleep loop is this kind of training, so without a fix we should expect the same.
- **Small models are the hard case.** With the same 10% mix, a 1.5B model's refusal rose only from 0.00 to 0.04, while
  7-8B models reached about 0.8 (shown in one paper). AbstentionBench, by contrast, says scaling helps little, so the
  size effect is unsettled.
- **Rewarding "abstain" as its own action can collapse into refusing everything** while the reward curve looks like it
  is improving (arXiv 2608.00301, one preprint, suggested). The proposed fix: the model always states a confidence,
  and the abstain threshold is applied only at test time.
- **Being able to solve a problem doesn't mean it can ask the right question about it** (QuestBench and ClarifyCodeBench, shown).
- **Asking too much comes from training, not from the base model** (When2Call, CoCoNot), so every "ask" item needs
  a solvable twin.

**Practice items where code can prove the right move:**
1. Impossible 24 hands, where the right move is "can't be done". Brute force with exact fractions: of the 1,820 hands
   from cards 1-13, 1,362 are solvable and 458 provably are not.
2. Missing-number puzzles, where the right move is to ask for the hidden number. An item is kept only if different
   hidden values lead to different answers. A correct question names the missing slot.
3. Ambiguous code tasks, where the right move is to ask which reading is meant. An item is kept only if two readings
   both pass the visible tests but differ on hidden tests.
4. Hard but solvable items, where the honest move is "I couldn't find it within budget, handing over". This scores
   0, less than solving.

**Proposed scoring:** a correct solve scores +1 and a wrong answer −1 or worse. An honest "can't" on a truly
impossible item scores +1, and the right question on a missing-info item also scores +1. Asking or giving up on a
solvable twin scores −0.25, which is the anti-laziness term. Start with 10% impossible and 10% missing-info items.

**Proposed pass marks (to be fixed in a PASSMARKS file before the run):**
- It says "can't" on at least 70% of held-out impossible hands.
- It asks or gives up on no more than 5% of solvable twins it could already solve.
- When forced to guess after abstaining on a solvable item, it is right no more than 30% of the time. A higher rate
  means the abstentions are lazy.
- On missing-number items, its question names the hidden slot at least 60% of the time.
- Accuracy on solvable items drops by at most 2 points.

**Proved wrong if:** "can't" stays at 10% or below (the small-model failure the evidence predicts), or false asks
rise along with correct asks (collapse).

## Suggested order

1. **Asking test on 24 puzzles.** Impossible hands plus solvable twins, $0 on the CPU, with the pass marks above. This
   is one change to the loop we already have.
2. **Wordle,** as the Bayesian-update test.
3. **Reasoning Gym calendar and time tasks, then function calling.** These are the first assistant chores.
4. **MBPP / APPS-intro coding with hidden tests,** then ambiguous-code asking items.

Registered one at a time, each against a placebo arm and the previous rung.
