# tgt-5 verification (creative thread, 2026-09-26)

Source: origin/builder-outbox artifacts/claude-tgt5-20260926/ (RESULTS-gpu.md, gpu/), copied unchanged to main.
Run: rental 52674236 (RTX 5090), exit rc=0, ~$0.19 of the $1.00 cap, code = unmodified origin/main (selftest ok).

## Registered verdict: PASS (confirmed)

Recounted from gpu/contrasts.json with claude_tgt5.boot_lower (same seed), not copied from the summary:
- W pairs with D > 0: 97 / 97 / 100 of 120 (bar: 84 in each seed). Met.
- Mean of (W's D averaged over seeds − base D): 1.3956 nats (bar 0.20), 98.33% bounds [1.0099, 1.797]. Lower bound > 0. Met.
- Inconclusive check: 179 won practice puzzles (≥ 20), 20 own greedy-correct (≥ 10). Conclusive.
- Panel checks: 120 pairs over 60 hands; every a makes g and not h, every b makes h and not g; 0 of 240
  (hand, target) items overlap the practice set (seed 9) or the DEV panel.

## Counts (masked D; raw in tgt5_summary.json)

| Model | Pairs D > 0 (of 120) | Mean D (nats) | Median D |
|---|---|---|---|
| base | 81 | 0.51 | 0.46 |
| W, own hits (seeds 0/1/2) | 97 / 97 / 100 | 1.53 / 2.07 / 2.11 | 0.86 / 1.06 / 1.11 |
| E, solver answers | 109 / 103 / 102 | 2.45 / 2.42 / 2.47 | 1.88 / 1.82 / 1.73 |
| C, known answers repeated | 89 / 87 / 81 | 1.82 / 2.12 / 2.68 | 1.42 / 1.82 / 2.28 |

## Diagnostics (NOT registered; description only, they change no verdict)

Seed-averaged, per pair, same hand bootstrap (98.33% bounds):
- C − base: +1.70 [1.06, 2.39]. W − C: −0.30 [−1.14, +0.51]. E − W: +0.54 [0.26, 0.86].

What this means for the question tgt-5 was meant to answer:
- Shown: sleeping on correct answers makes the 1B match answers to their own targets better (all three arms).
- Shown here, and it limits the PASS: C, which COLLAPSES coverage in blurt-5s (77 → 11-14 puzzles), raises
  target matching about as much as W in mean D (the W − C interval spans 0). It helps fewer pairs (81-89 vs 97-100)
  but by larger amounts. So better target matching is real but is NOT what separates the sleep that widens
  coverage (W, E) from the one that collapses it (C).
- Suggested: what separates them is breadth, i.e. many different newly won puzzles vs a few repeated ones, which
  fits the reviewer's earlier reading ("a broader spread over hard problems").
- E again edges W (as in blurt-5s coverage). Being self-made still adds nothing on this measure.
- The registered marks had no control arm; that was a gap in the design (adopted unchanged from the reviewer).
