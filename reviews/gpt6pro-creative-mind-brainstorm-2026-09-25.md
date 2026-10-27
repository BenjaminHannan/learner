You are a research partner. I'm Ben, a high-school senior building a small AI model as a personal project. I'd like to brainstorm with you and have you think deeply and critically. You can't see my code, so everything you need is below. Where my framing is wrong, say so.

## What I'm building

It's a small assistant built around a "brain-like" design. The chat model is MiniCPM5-1B, a 1-billion-parameter open model, used with its thinking mode off. It has these parts:
- a **notebook**: an exact memory of facts the user taught it; it never guesses facts;
- a **reasoner**, which should do most of the work;
- a **creative mind**, a generator that "says random stuff, then gets filtered", whose goal is to maximise the number of lucky hits;
- **sleep**: when idle, the model improves itself by training on what worked.

Everything below comes from small experiments on number puzzles. These puzzle results are separate from the full assistant, and nothing here has been tested inside it yet. Please keep the two apart in your answer.

## The creative loop as it works today (tested on number puzzles)

**Puzzles.** Use each given number exactly once, with + − × ÷ and brackets, to make a target. Two thirds of the puzzles have 3 numbers from 1-9 and a target from 5-40. One third are 4 numbers from 1-13 with target 24.

**Steps:**
1. The reasoner (the 1B's single greedy answer) tries the puzzle.
2. If it misses, the model makes 30 "blurts": random samples at temperature 1.5, chosen on a separate practice set.
3. A "rule keeper" restricts sampling to legal expressions over exactly the given numbers. At each step only tokens that keep the text a legal prefix are allowed, and the model's own probabilities choose among them.
4. An exact checker keeps the right blurts ("lucky hits").
5. "Sleep" trains a small LoRA adapter (rank 16, 3 epochs) on the model's own correct answers plus the first lucky hit from each won puzzle.

**Controls:**
- **C:** the model's own correct answers only, repeated to the same number of examples.
- **P** (placebo): wrong blurts instead of lucky ones.

## Results so far (fresh test puzzles the model never practised on; pass marks registered before each run)

**Sleep, then measure the reasoner's single greedy answer.** Registered FAIL in 3 versions; the gains were small and unstable.

| Run | Before | Sleep on lucky hits (W) | Control C | Bar |
|---|---|---|---|---|
| blurt-2, CPU (150 puzzles) | 6 | 15, 19 | 6, 6 | passed |
| blurt-2, GPU repeat | 6 | 13, 11 | – | needed +8, got +6: FAIL |
| blurt-2p (placebo) | – | – | – | W minus P was +4, needed +5: FAIL |
| blurt-2b (train on every distinct hit) | – | – | – | FAIL; its "proved wrong" clause triggered |

**Sleep, then measure luck: lucky blurts out of 30 per fresh puzzle.** Registered PASS and replicated.

| Run | Before | W (sleep on own lucky hits), seeds 0/1 | C (sleep on known answers only) |
|---|---|---|---|
| blurt-3, CPU (66 puzzles × 30) | 63 | 126 / 136 | 85 / 87 |
| blurt-3r, GPU, new seeds (67 × 30) | 59 | 129 / 148 | 59 / 58 |

Puzzles with at least one lucky blurt:
- blurt-3: 27 before, 38 / 38 after W, but 3-4 after C.
- blurt-3r: 29 before, 40 / 43 after W, 3-4 after C.

So training on repeated known answers collapses the variety of guesses, and training on fresh checked hits keeps it.

**Ideas (gift suggestions for a user, no exact checker):**
- About 15% of raw blurts were rated good by blind judges.
- 9 of 10 requests had at least one good idea among their 30 blurts.
- The 1B judging its own ideas picked a good one first on 2 of 10 requests.
- An open-weights teacher model (GLM) agreed with blind judges on 256 of 300 labels.
- A small classifier on the 1B's hidden states, trained on teacher labels, picked a good idea first on 3 of 10 and had a good one in its top 3 on 7 of 10.

**Running now: "can't" (ask-24).**
- I let the model answer "none" when a puzzle is impossible. Code can prove this by brute force: of the 1,820 four-card hands from 1-13, 458 can't make 24.
- Surprise: the base 1B then said "none" on 20 of 20 impossible practice puzzles AND on 20 of 20 solvable ones, and 576 of 600 of its blurts were "none". Published work warns about the opposite problem: training on your own successes erases refusals.
- The test now asks whether sleep, with verified "none" examples on impossible puzzles only, teaches it to tell possible from impossible:
  - "none" on at least 70% of impossible puzzles;
  - "none" on at most 30% of solvable ones;
  - the gap beats a control that never sees "none".

## What I've learned from reading (my summary of papers; please correct anything wrong)

- Learned intuition guides real search, but only within a family of similar problems (AlphaGeometry 14→25 of 30 with learned guesses; the No Free Lunch theorem).
- Every self-improving system that worked on hard real problems kept an exact check at the end: AlphaZero, AlphaProof, FunSearch, AlphaEvolve, DeepSeek-R1. Training directly on a fuzzy learned judge rises and then falls (reward over-optimisation).
- "22 is close to 24" is a bad warmth signal. Distance-shaped rewards failed in Hindsight Experience Replay. Two things worked:
  - relabel a miss as a hit for the goal it did reach;
  - judge whether a partial state can still reach the goal (Tree of Thoughts took GPT-4 from 4% to 74% on the 24 game).
- Training on your own hits can raise first-try accuracy while shrinking what the model can find with many tries (Yue et al. 2025; disputed by ProRL).
- In one study, random rewards gave most of the gain real rewards did (21.4 of 29.1 points), so placebo arms matter.
- Higher temperature is weakly linked to novelty and moderately linked to incoherence.
- Judging ideas is hard even for experts: the best LLM judge agreed with experts 53.3% of the time, against 56.1% expert-to-expert and 50% chance.
- Across 22 famous discoveries, the most common ingredients were:
  - an exact test at the end;
  - building on others' work;
  - persisting through failure;
  - noticing a number that didn't fit;
  - a strict principle trusted until it forced a prediction;
  - reframing the problem.

  Sleep or dream insight showed up in only about one real case.

## Designs I'm considering (none built yet)

1. **"Egg" search.** The model keeps a belief (several "lobes") about where answers probably are. It samples guesses from that belief, updates on what it finds, and writes the update into its weights during sleep. Randomness grows when ideas keep failing ("a growing circle").
2. **A partial-progress judge.** "Can the leftover numbers still reach the target?", with labels computed by brute force, plus hindsight relabelling.
3. **Reframing.** Blurt restated versions of the problem (another target, 3 of the 4 numbers, working backwards), solve those, and carry the pieces back.
4. **A pieces library.** Store checked sub-results and "off-target hits" as reusable building blocks, retrieved by shape.
5. **Surprises first.** Puzzles where the model's own expectation disagreed with the checker get practised first.
6. **Choosing what to practise.** Keep puzzles it solves sometimes but not always.
7. **A ladder toward the real world, climbing by how exact the check is:**
   - Reasoning-Gym puzzles;
   - Wordle, where every guess gets exact feedback;
   - Lichess chess puzzles;
   - function calling;
   - beginner coding with hidden tests;
   - harder coding;
   - SQL;
   - real GitHub issues.

   Fuzzy tasks like ideas would only train on ideas a real person confirmed.
8. **Asking a human** when something really can't be solved, with rewards that punish lazy asking on solvable twins.

## What I want from you

1. **Challenge my picture of a "creative mind".** What's missing, wrong, or backwards? Is "maximise lucky hits, then learn from them" the right core, or does it miss what makes creativity different from search?
2. **Explain the replicated luck result.** What does "sleep on own lucky hits roughly doubles luck; sleep on known answers collapses variety" most likely mean mechanically, for example distribution sharpening versus learning structure? What would tell those apart?
3. **Explain the "none on everything" surprise.** Why would a 1B give up on everything when offered "none", while papers find big models over-answer? How should that change the design?
4. **Rank my designs 1-8** by expected gain per unit of effort for a 1B on a laptop GPU (RTX 5070 Ti, 16 GB), and name anything better that I haven't listed.
5. **Propose the next 3 experiments, each ONE change from what exists.** For each give:
   - the pass marks, fixed in advance with exact numbers;
   - a control or placebo arm;
   - the result that would prove the idea wrong.
6. **Reaching the real world.** Where do you expect puzzle gains to stop transferring to real assistant work (coding, answering questions)? What is the smallest test that would tell us?

Rules for your answer:
- Label every claim as **shown** (measured, cite it), **suggested** (argued or indirect) or **untested**.
- Keep the puzzle experiments and the full assistant separate.
- Prefer one change at a time.
- Don't invent citations. If you're unsure a paper exists, say so.
- End with a plain-language summary I can read in two minutes.
