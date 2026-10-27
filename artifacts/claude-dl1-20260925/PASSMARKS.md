# dl-1: which night learning rule makes the 1B better at the day's work, fast, without harm elsewhere?
(Fix-sleep thread. Registered when this file is committed, before the run.)

Why:
- Ben (19:22-19:37 UTC 2026-09-25) set the goals:
  - nights should almost always make the model better, as RL does;
  - "the model should rapidly improve for the work that it does day to day", and also for other things;
  - bored mode and sleep should be one downtime-learning loop.
- Research (reviews/sleep-nights-research-2026-09-25/REPORT.md) says:
  - our nights are copy practice on lucky hits (rejection-sampling fine-tuning);
  - learning from the model's own right AND wrong tries (on-policy RL) forgets less and keeps more variety;
  - an RL test needs a shuffled-reward placebo.
- Nobody has measured whether our nights harm the 1B elsewhere.

Code: scripts/claude_dl1_nights.py (docstring = method). Model: plain MiniCPM5-1B, thinking off, no download.

Loop:
- Each arm and seed runs 3 day/night cycles on ONE growing adapter (LoRA r16, q,k,v,o).
- Day: 150 new number puzzles. On each, the model gives 1 greedy answer and 30 guesses at T 1.5, and the exact checker
  marks every guess.
- Arms (the ONE change between S and R is the learning rule):
  - S (copy practice) = blurt-3's night: 3 epochs of cross-entropy, lr 2e-4, on the greedy right answers plus the
    first lucky hit on each miss.
  - R (reward learning) = REINFORCE with a group-mean baseline, one pass, over groups with both right and wrong
    guesses.
  - Z (placebo) = R with the day's rewards shuffled.
- R's learning rate comes from a registered DEV rule. On shifted DEV seeds, one night from the base at 2e-5 and at
  1e-4; the lr with more right guesses on 40 DEV test puzzles x 20 is kept (a tie keeps 2e-5).

Measured after every night (never trained on):
- TEST: 100 fresh puzzles of the same kind as the day's work, 20 guesses each. Counts: right guesses ("lucky"),
  puzzles reached, greedy solves.
- HARM: 300 fixed general items (capitals, opposites, plurals, orders, counts, bigger number), counted as 1->0 and
  0->1 flips against the base.
- KL: KL to the base on the base's own replies to 60 prompts.

## Marks (means over seeds 0 and 1 unless stated; L0 = base lucky on TEST)
- R1 fast gain on the day's work: R final lucky ≥ 1.5 × L0 and ≥ 0.8 × S final lucky.
- R2 less harm (net harm = 1->0 flips minus 0->1 flips at the end):
  - if S's net harm ≥ 10: R ≤ 0.5 × S, and each R seed ≤ each S seed;
  - otherwise: R ≤ 5 on each seed. The safety comparison is then untestable and is reported as such.
- R3 variety: R puzzles reached ≥ the base's, on each seed.
- R4 not a placebo effect: R ≥ 1.2 × Z, and each R seed > each Z seed.
- R5 nights keep helping: at most 1 of R's 6 nights where TEST lucky falls by more than 15% vs the night before.
- PASS = R1-R5.
- INCONCLUSIVE if L0 < 10, or if any R seed's first day has fewer than 40 groups with mixed right and wrong guesses.
- Proved wrong: R's mean lucky ≤ Z's, or (S net harm ≥ 10 and R net harm ≥ S net harm).
- Reported, not marked: greedy solves, KL, per-night harm and gain for all arms, and the night-1 gain (how fast).

Limits stated before the run:
- One kind of work (number puzzles). Code, tools and chat join in later tests.
- REINFORCE here has no clipping and no KL term (one pass per day, so there is no stale-sample ratio to clip).
- The harm panel is short general questions, not chat quality.
- A per-family adapter (research Q8) and nightly replay are later single changes.
