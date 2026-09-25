# VERIFY blurt-3r (replication of blurt-3): PASS, so blurt-3 is REPLICATED (checked 2026-09-25 by the creative thread)

Rule: PASSMARKS-blurt3.md, section "Replication blurt-3r": same command and marks, --train-seed 6 --test-seed 781
--n-test 80, on BensPC. Run: builder-outbox runs/002b-blurt3r-loop (rc=0, 31.1 min, GPU). The command in
RESULTS-gpu-3r.md matches the registered one. Numbers below are recomputed from gpu-3r/loop_summary.json.

| | lucky blurts (of 67 x 30 = 2,010) | puzzles with at least one lucky blurt (of 67) | greedy solves |
|---|---|---|---|
| before (L0) | 59 | 29 | 1 |
| W seed 0 / 1 (sleep on own hits) | 129 / 148 (mean 138.5) | 40 / 43 | 6 / 6 |
| C seed 0 / 1 (sleep on known answers only) | 59 / 58 (mean 58.5) | 4 / 3 | 2 / 2 |

- U1: mean W 138.5 ≥ 1.5 × L0 = 88.5. PASS.
- U2: mean W 138.5 ≥ 1.3 × mean C = 76.1, and each W seed (129, 148) > each C seed (59, 58). PASS.
- Not inconclusive: 158 won practice puzzles (≥ 20), L0 59 (≥ 10). DEV temperature rule chose 1.5 (46 vs 27).
- Proved-wrong clause (mean W ≤ mean C): not met.

Verdict: blurt-3r PASS. Together with blurt-3 (CPU, seeds 5/780: 63 -> 126/136 vs C 85/87), the result replicates
on new practice and test seeds, on a different machine. Sleeping on its own checked lucky hits about doubles and a
bit more the 1B's lucky guesses on fresh puzzles. Sleeping only on known answers again collapses variety (puzzles
reached 29 -> 3-4).
Limits: one puzzle family (3-4 numbers, targets 5-40 / 24); luck, not the reasoner's first answer (greedy solves
6 vs 1, a secondary measure); 67 test puzzles.
