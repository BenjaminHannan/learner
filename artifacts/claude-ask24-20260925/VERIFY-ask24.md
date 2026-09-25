# ask-24 result: PROVED WRONG — sleep with verified "none" examples did not teach the 1B to tell possible from impossible

Marks: PASSMARKS-ask24.md (main a3ee91fcb). Note: that commit landed 3 s AFTER the run process started, and before
the run had printed any result. The marks text had been written, and shown to Ben on a card, before the launch.
Run: the creative thread's container CPU, 201 minutes. Summary: cpu/ask24_summary.json. Fresh test: 71 solvable + 78
impossible puzzles (overlap with practice dropped from 80 + 80).

| | Impossible answered none (of 78) | Solvable answered none (of 71) | Gap G (points) | Solvable right, greedy | Lucky blurts / puzzles hit (solvable) |
|---|---|---|---|---|---|
| base | 78 | 71 | 0 | 0 | 87 / 33 |
| W seed 0 (no "none" examples) | 0 | 0 | 0 | 8 | 148 / 42 |
| W seed 1 | 0 | 0 | 0 | 9 | 184 / 44 |
| N seed 0 (+40 verified "none") | 78 | 70 | 1.4 | 1 | 137 / 42 |
| N seed 1 | 78 | 71 | 0 | 0 | 179 / 47 |

Practice: the base reasoner said none on all 40 impossible AND all 360 solvable practice puzzles (0 right). 164 of
the 360 solvable puzzles were won by blurts (349 lucky of 10,800). Verified none hits: 40. Neither inconclusive
clause triggers (40 ≥ 20 none hits; 164 ≥ 20 wins).

Against the marks:
- A1 (N imp_none ≥ 70%): MET (100%).
- A2 (N sol_none ≤ 30%): NOT MET (99.3%).
- A3 (N gap ≥ 40 points and above W's): NOT MET (mean 0.7).
- A4 (N luck ≥ 0.8 × W): MET (158 vs 166 mean lucky blurts, 0.95×).
- Proved wrong (N gap ≤ 10 points): MET. Verdict: PROVED WRONG.

What it means (shown, puzzles only): sleep did not teach WHEN "can't" is right. Training on expressions alone (W)
erased "none" completely (0/78 on impossible puzzles), as the papers warned. Adding 40 verified "none" examples (N)
kept "none", but everywhere. When N said none on a solvable puzzle and was forced to try, it was right 7 of 70-71
times. The luck gain from sleep was not taxed.
Together with ask-24ab (frozen 1B: "yes" on 240/240 A/B, "none" on 240/240), this suggests the 1B has no usable
sense of which 24-hands are solvable. So a "can't" answer should come from code proof or a learned judge, not from
the model's own word. feas-24b's head (77-79% on partial states) is the closest thing so far. Untested: sleep with
matched solvable twins, where the base first answers with an expression.
Checks: every row's counts add up (imp_none + imp_expr = 78, and sol_none ≤ 71). G was recomputed by hand from the
counts above.
