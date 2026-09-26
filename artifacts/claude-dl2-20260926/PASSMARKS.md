# dl-2: a week of copy-practice nights on the 1B. Does it keep getting better, night after night, without harm?
(Fix-sleep thread. Registered when this file is committed, before the run.)

Why:
- In dl-1 (registered FAIL, artifacts/claude-dl1-20260925/VERIFY.md), the treatment (REINFORCE) lost.
- Its reference arm, S = copy practice on each day's checked right answers, improved on all 6 nights:
  - right guesses on fresh puzzles went 69 -> 160 and 169;
  - no night fell more than 15%;
  - the 300-item general panel went up.
  That was 3 nights and not a registered claim.
- Ben wants nights that almost never make the model worse and that keep improving it at the day's work.
- Creative's blurt-5s showed that right answers on new puzzles are the good material.

Code: scripts/claude_dl2_nights.py (docstring = method). It reuses claude_dl1_nights (gather, train_copy, measure,
harm panel, KL) unchanged. Model: plain MiniCPM5-1B, thinking off, no download.

ONE change from dl-1's S arm: 7 nights instead of 3. It runs on new seeds 2 and 3 and a new fresh TEST set
(seed 3890, 100 puzzles x 20 guesses).
- S = copy practice: the day's greedy right answers plus the first lucky hit on each miss; 3 epochs, lr 2e-4, one
  growing adapter.
- P = placebo: the same number of examples, but each is a legal, complete WRONG guess from that day. S and P differ
  only in whether the practised answers are right.
- Measured after every night:
  - TEST: right guesses ("lucky"), puzzles reached, greedy solves;
  - HARM: the same 300 general items as dl-1, counted as flips vs the base;
  - KL to the base.

## Marks (on S; L0 = base lucky on TEST; 14 S nights = 7 nights x 2 seeds)
- W1 better after a week: S final lucky ≥ 2 × L0, on each seed.
- W2 nights rarely hurt the day's work: at most 1 of the 14 S nights has TEST lucky more than 15% below the night
  before. Night 1 is compared with L0.
- W3 nights rarely hurt anything else: at most 1 of the 14 S nights has net harm > 5 on the panel (lost minus gained
  vs base), and final net harm is ≤ 0 on each seed.
- W4 variety kept: S final puzzles reached ≥ base, on each seed.
- W5 the right answers caused it: S final lucky ≥ 1.3 × P (sums over seeds), and each S seed > each P seed.
- PASS = W1-W5. INCONCLUSIVE if L0 < 10.
- Proved wrong: S final lucky ≤ 1.1 × L0 on either seed, or ≥ 3 worse S nights, or S ≤ P.
- Reported, not marked:
  - greedy solves;
  - KL per night;
  - the night-by-night curve, i.e. whether gains flatten after night 3.

Limits stated before the run:
- One kind of work (number puzzles).
- The panel gain in dl-1 may be answer-format learning; W3 guards against harm only.
- 14 nights cannot show "1 in a billion"; W2 and W3 are the honest version at this size.
