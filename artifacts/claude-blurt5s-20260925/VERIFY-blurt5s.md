# blurt-5s result: PROVED WRONG — the model's OWN lucky hits are not special; exact-solver answers teach as well or better

Marks: PASSMARKS-blurt5s.md (main b9ede7a23, registered before the rental). Run: vast RTX 5090 (the builder's
RESULTS-gpu-5s.md, copied here from builder-outbox), 17.8 minutes, about $0.24, pinned model 87179e5c. I recounted S1
and the proved-wrong clause from gpu-5s/blurt5s_summary.json and they agree with the builder.

Test: 184 fresh puzzles (56 overlap drops from 240, so the margin D = 19), 30 samples each at T 1.5 (DEV-chosen).
Practice: 20 own right answers + 191 won puzzles, so 211 examples in every arm.
| Arm | Puzzles solved in 30 tries, seeds 0 / 1 / 2 | Solved on the 1st try | Lucky samples |
|---|---|---|---|
| before sleep | 77 | 3 | 167 |
| W (own lucky hits, the blurt-3 recipe) | 112 / 108 / 110 | 8 / 9 / 8 | 287 / 326 / 344 |
| E (the same puzzles, exact-solver answers) | 123 / 113 / 117 | 12 / 14 / 12 | 429 / 429 / 409 |
| C (known answers repeated) | 14 / 12 / 11 | 9 / 7 / 8 | 237 / 238 / 237 |

- S1 (W ≥ E + 19 in every seed, and the interval excludes zero): NOT MET. W − E = −11 / −5 / −7; the 95% interval
  for W − E is [−8.7, +0.5] points.
- Proved wrong (E ≥ before + 19 in every seed, and the upper bound of W − E is below +5): MET (E +46 / +36 / +40;
  upper bound +0.5). Verdict: PROVED WRONG.

What it means (puzzles only):
- Shown: blurt-3's gain comes from sleeping on CORRECT answers to NEW puzzles, not from the answers being the model's
  own. Solver answers on the same puzzles did at least as well, and were a little better on every seed.
- Caveat: the solver answers were shorter on average (6.96 vs 8.13 characters), so "shorter answers teach better" is
  not ruled out (untested).
- Shown again, strongly: sleeping on repeated known answers (C) collapsed variety. It solved 11-14 puzzles in 30
  tries, against 77 before sleep.
- Design consequence (suggested): the creative loop's job is FINDING checked answers where no solver exists. Being
  self-made adds nothing. Where a solver or teacher exists, its checked answers are as good as creative hits.
