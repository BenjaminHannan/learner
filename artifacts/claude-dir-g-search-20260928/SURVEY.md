# dir-g survey: search inside the thought (helper G, 2026-09-28)

Labels: CHECKED = confirmed by a web search this session (sources below). RECALLED = from memory, not re-checked here; treat as leads.
Nothing was run. Question: what has been shown about letting a network try several lines of thought and keep one, and what fits a small learned loop that is never told the puzzle kind?

## Plain summary (for Ben)
- The same puzzle (make 24 from four numbers) has been attacked before. Big language models fail it when they answer in one go (CHECKED: GPT-4 solved 4% with chain-of-thought) and do far better when they are made to try several options and judge them (CHECKED: 74% with Tree of Thoughts). But there the trying and judging is done by hand-written code around the model, which our rules forbid.
- Work that puts the search inside the model exists: train on written-out search traces (Stream of Search, CHECKED: +25% over models that only see the best path; further self-training solved 36% of problems the code solvers could not) and keep several options alive in the hidden state (Coconut, CHECKED: the thought vector can hold many search branches at once, shown on graph reachability and maths).
- Almost all of it starts from a big pre-trained model or from search traces written by a solver. Our loop is small and trained from scratch on answers only, so how much carries over is UNTESTED.
- The cheapest idea that stays learned and kind-blind: run several starts of the same loop, train so that they differ, and let the net's own check head pick. That is the design in DESIGN.md.

## Prior work
| # | Work | What it shows | Fit to us | Label |
|---|---|---|---|---|
| 1 | Tree of Thoughts (Yao et al. 2023, arXiv 2305.10601) | Game of 24: 4% one chain, 74% with propose / evaluate / backtrack | Same puzzle. Search and judge are prompting code, i.e. hand-written. Shows the puzzle is solvable by trying options | CHECKED |
| 2 | Stream of Search (Gandhi et al. 2024, arXiv 2404.03683) | Countdown (24 generalised): a model trained on serialised search traces beats one trained on best-path only by 25%; STaR and APA then solve 36% of previously unsolved problems | Search learned inside the model. Needs solver-written traces (code-made, so allowed as data), a bigger change than one knob | CHECKED |
| 3 | Coconut / continuous thought (Hao et al. 2024, arXiv 2412.06769; superposition analysis 2505.12514) | Hidden state fed back as the next input can carry many alternative next steps (a breadth-first search) | Our loop already feeds its state back. Suggests the state can hold several candidates without extra streams | CHECKED |
| 4 | Verifiers, best-of-N (Cobbe et al. 2021, GSM8K) | Sample many answers, a trained verifier picks one; beats single-sample fine-tuning | Exactly "several tries, learned check". The verifier needs to be discriminative on unseen items | RECALLED |
| 5 | Self-consistency (Wang et al. 2022) | Vote over sampled chains | Needs answers that repeat; a puzzle with many valid answers votes poorly | RECALLED |
| 6 | STaR / expert iteration (Zelikman 2022; Anthony 2017) | Keep only tries that a checker accepts, train on them | The "search then learn from what worked" step. A separate, larger change (DESIGN.md section 6) | RECALLED |
| 7 | Deep-thinking / looped nets (Schwarzschild et al. 2021; Bansal et al. 2022) | Looped nets extrapolate to harder mazes and sudoku by thinking longer; a path-independent state is a stable fixed point | Explains why our extra rounds do not help: the state settles. Different starts give different fixed points only if the net is trained for it | RECALLED |
| 8 | HRM / Tiny Recursive Model (2025) | Small recurrent nets on sudoku, mazes, ARC with a learned halt | Close to our loop and its halt head. No search over candidates as far as I recall | RECALLED |
| 9 | Winner-take-all / multiple-choice learning (Guzman-Rivera et al. 2012; Lee et al. 2016) | K heads, only the best one is trained on each item, so the heads specialise and give diverse guesses | The training trick that keeps K streams from collapsing to one answer | RECALLED |

## Reading (SUGGESTED, from the table plus our diagnosis)
1. Tree-of-thought style search needs two abilities: propose different candidates and judge them. Our diagnosis (DIAGNOSIS.md section 1, cause 2) says the judging ability, arithmetic checking, is exactly what the nets lack. Trying more candidates without a checker would only reach the no-arithmetic floors (a few of 300).
2. So the informative question is not "does the net find answers" but "does its check head learn to tell a right answer from a wrong one on unseen hands". A stream design measures that separately from candidate quality (oracle pick vs the net's pick).
3. Brain view (simplified textbook, not checked): people hold a few options in working memory, evaluate each against the goal, drop the losers. Silicon can do better on the parallel part: all options run at once with exact bookkeeping.
4. Not chosen here: writing solver traces for the net to imitate (Stream of Search). It works, but it teaches the numbers kind by construction and is a large change. It stays the fallback.
5. Not chosen here: feeding the answer back each round (H9's R3 "Refill"). That is sequential try-and-revise, another thread's design; G should not duplicate it.

## Sources checked
- https://arxiv.org/pdf/2305.10601 (Tree of Thoughts); https://arxiv.org/abs/2404.03683 (Stream of Search); https://arxiv.org/pdf/2412.06769 and https://arxiv.org/pdf/2505.12514 (Coconut and superposition).
