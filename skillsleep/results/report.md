| arm | retail test | airline test | ARC-Easy |
|---|---|---|---|
| A0 | 63.7% (102/160) | 60.0% (24/40) | 71.0% (142/200) |
| A1 | 68.1% (109/160) | 52.5% (21/40) | 71.0% (142/200) |
| A2 | 66.9% (107/160) | 57.5% (23/40) | 71.0% (142/200) |

day retail_train: 99/148 runs pass

fix retail_train_retry: 9/33 runs pass

| comparison | delta (points) | p | tasks |
|---|---|---|---|
| retail A2 - A0 | +3.1 | 0.5728 | 40 |
| retail A2 - A1 | -1.2 | 0.8777 | 40 |
| retail A1 - A0 | +4.4 | 0.3799 | 40 |
| airline A2 - A0 | -2.5 | 1.0000 | 20 |
| ARC-Easy A2 - A0 | +0.0 | 1.0000 | 200 |
P1 sleep teaches skill: FAIL - A2 retail test >= A0 + 6 points and p < 0.05
P2 bad examples add something: FAIL - A2 >= A1 + 4 points and p < 0.05
P3 skills carry over (label only): FAIL - A2 airline test >= A0
P4 no harm: PASS - A2 airline >= A0 - 7.5 points and ARC-Easy >= A0 - 2 points
Wrong if A2 <= A0 on retail test: no
Wrong if A2 < A1 - 4: no
Day-1 sanity: A0 retail test 63.7% vs Swap-1 64% -> gap -0.3 points  (within 15)
