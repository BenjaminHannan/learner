# feas-24b result: NOT SHOWN (near miss) — registered 20:05:35 UTC, run 20:06-20:18 UTC

Marks: PASSMARKS-feas24b.md (main 101a49e08, committed before launch). Run: the creative thread's container CPU,
2 threads, 12.5 minutes. Summary: cpu/feas24b_summary.json. Dev picked layer 16 with l2 100 (mean dev AUC 0.810;
per seed 0.812 / 0.806 / 0.812). Every fit converged (the largest final gradient was 6e-9, far under the 1e-4 limit).

Pairs ranked right, of 200 (ties count half):
| Seed | Real labels | Shuffled labels | Real minus shuffled | Real, 3-value pairs (of 100) | Real, 2-value pairs (of 100) |
|---|---|---|---|---|---|
| 0 | 158 | 111 | +47 | 71 | 87 |
| 1 | 155 | 95 | +60 | 68 | 87 |
| 2 | 153 | 95 | +58 | 69 | 84 |

- At least 150/200 in every seed: MET (153-158).
- At least 30 above shuffled in every seed: MET (+47 to +60).
- At least 70/100 on the 3-value pairs in every seed: NOT MET (71, 68, 69).
- Registered verdict: NOT SHOWN, since PASS needs all three and the proved-wrong clause is far from met.
- Reproducibility: a re-score from the same cached features with 4 threads (recount/feas24b_summary.json) matched
  every count exactly. The test pairs use 74 distinct live 3-value states and 24 distinct live 2-value states, and
  none of them was in training.

What it means for the puzzles only:
- Shown: a cheap logistic head on the frozen 1B's layer-16 state ranks a still-solvable 24-game state above a dead
  end from the same hand in about 77-79% of pairs. The label-shuffled placebo scores 48-56%.
- Shown: it is weaker on the harder 3-number states (68-71%) than on 2-number states (84-87%), which is where
  search needs it most. It missed the fixed 70% bar there in 2 of 3 seeds.
- Suggested: it is a real but modest signal. Per the reviewer, it could only ever be a soft priority in search,
  never a pruning rule. Whether it speeds up search is untested, and would need its own registered test.
- This result is not re-run to get over the bar.
