# dl-3 VERIFY (Fix-sleep thread, 2026-09-26 ~05:35 UTC)

**Registered verdict: FAIL.** F1 and F2 fail; F3, F4 and F5 pass. Not inconclusive, and the proved-wrong clause is
not met.

The builder scored it FAIL (RESULTS-gpu.md). A blind recount agrees. The recounting agent read only PASSMARKS.md and
gpu/dl3_results.json and used its own script, not the scorer, the marks key or RESULTS.

Data checks hold:
- 7 nights per arm and seed, on seeds 4 and 5.
- net = lost − gained, and right = 200 − lost + gained.
- sum(harm_items) = right.
- harm_vs_prev matches a recount from the per-item panels.

| Night 7 | Base | S s4 | S s5 | A s4 | A s5 | Bar |
|---|---|---|---|---|---|---|
| panel lost (right at base, wrong now) | | 39 | 24 | 20 | 36 | F1: A sum ≤ 0.5 × S sum (56 vs 31.5) and each A < each S: **FAIL** |
| A nights with lost > 10 | | | | 6 of 7 | 5 of 7 | F2: ≤ 1 of 14 (was 11): **FAIL** |
| TEST lucky | 59 | 171 | 257 | 227 | 216 | F3: ≥ 118 each, and A gain 325 ≥ 0.8 × S gain 310: **PASS** |
| worse nights (> 15% drop) | | | | 0 | 1 | F4: ≤ 1 of 14: **PASS** |
| puzzles reached | 30 | 60 | 55 | 53 | 59 | F5: ≥ 30: **PASS** |
| KL to base on general replies | | 0.17 | 0.13 | 0.28 | 0.28 | report |

Lost per night:
- S s4: 3, 11, 15, 17, 20, 35, 39
- S s5: 4, 8, 11, 12, 13, 14, 24
- A s4: 10, 15, 22, 16, 18, 17, 20
- A s5: 7, 10, 13, 16, 32, 41, 36

## What it means
- Copying the base's own greedy answers to general questions did not stop the forgetting. It made the first nights
  worse: 7-10 lost at night 1 vs 3-4 without replay.
- It also doubled drift from the base on general replies, and the drift was already 4-5 times higher at night 1
  (0.15-0.17 vs 0.03-0.04).
- The learning itself was kept (F3), so replay did not stop the day's gains.
- Likely cause (SUGGESTED, not shown): training on the base's single greedy answer sharpens the model toward one
  reply instead of holding its whole answer distribution where it was.
- The 1:1 mix also doubled the number of training steps.
- The fix this points at is matching the base's full next-token distribution (a KL anchor), not its greedy text.
  That is dl-4.
- Seed variation is large even without replay (S lost 39 vs 24 at night 7). Two seeds cannot separate a small
  effect from noise.

## Run facts
- RTX 5090 rental, 81 min, about $0.86. Replay pool 908 pairs.
- Code origin/main, unmodified; inputs byte-identical across a main move mid-run.
- The first rental host never started (~$0).
- The builder could not push its commit, and the results reached builder-outbox by the watcher.
