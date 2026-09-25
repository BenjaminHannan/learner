# feas-24 result: NOT SHOWN, and the test was broken — the head's training diverged (registered 19:41:02 UTC; run 19:42-19:56 UTC)

Marks: PASSMARKS-feas24.md (main d7910e060, committed before the chained run started at 19:42). Run: the creative
thread's container CPU, 13.8 minutes. Summary: cpu/feas24_summary.json. Layer 16, l2 1 chosen on dev (dev AUC 0.789).

Registered run, pairs ranked right of 200 (ties count half):
| Seed | Real labels | Shuffled labels | Real 3-value pairs (of 100) |
|---|---|---|---|
| 0 | 144.5 | 79 | 71 |
| 1 | 90 | 123.5 | 48.5 |
| 2 | 115 | 80.5 | 55 |

- PASS needs at least 150 in every seed: not met (the best seed got 144.5).
- Proved wrong needs 110 or fewer in all three seeds: not met (seed 0 got 144.5, seed 2 got 115).
- Registered verdict: NOT SHOWN.

Verification found a defect. It is shown, and it means the verdict says nothing about the idea itself:
- A recount from the same cached features (recount/feas24_summary.json; same code, but 4 CPU threads instead of 2)
  gave different real-label numbers: 151.5 / 151.5 / 91.5. The shuffled-label numbers were almost the same
  (80 / 123.5 / 80.5).
- Cause: the logistic fitter reused from the idea judge (claude_cre333e_train.fit_lr: plain gradient descent, step
  0.5, 400 steps) DIVERGES on these 1,536-number features. On seed 0 at layer 16, the training loss went from 0.69
  at the start to 8-47 and swung around; the scores reached ±200-350. A diverged fit is chaotic, so tiny rounding
  differences from the thread count change which pairs it ranks right. The seed-to-seed swings (90 to 144.5, and a
  shuffled head at 123.5) come from this, not from the data.
- So feas-24 did not test "can a cheap head rank live states above dead ends". It stays NOT SHOWN on the record.
  The follow-up changes only the fitter (feas-24b, registered separately, on a fresh panel).
- Knock-on (suggested, unchecked): the idea-judge head (claude_ideajudge_head.py, DEV only, "good idea first on
  3/10") used the same fitter, so it may have diverged too. Anyone reusing that head should re-fit it with a
  converged fitter before trusting it.
