# Fix screen v2: the exit pipe, and does the core matter at all?

Written 2026-10-04 22:27 UTC, before any run. Fast lane. Follows fix screen v1 (`../fix-screen-v1/results/RESULT-v1.md`): reader width, 8 rounds, lr 3e-4 and the pointer exit all left fit at ~48-50%.

## Runs (Ben's PC, sequential; same setup as screen v1)
Start main2 (copy path). Worst-8 families: chain_ops,state_update,cipher_map,chain_story2,var_chain,seq_cycle,fewshot_number_rule,group_induct.

1. **Z (lesion, eval only):** main2 with the 8 pooled core vectors zeroed (`--zero-pool`); the LM still sees all prompt words. Scored on all 1,360 in_dist rows. Compare: main2 intact = 68.5% (plateau diagnosis).
2. **X1-X3 (wider exit):** `--prefix-hidden 256`, the StatePrefix 259->32->2048 becomes 259->256->2048, function-preserving. 2,000 fixed rows, 3 passes, 6,000 updates, seeds 1-3. Baseline = diagnosis F1-F3 at 6,000: fit 50.6 / 52.5 / 46.3.

## Marks (fixed now)
- **Z:** "core carries little" if zeroing drops in_dist by under 10 points (>= 58.5%). "Core matters" if it drops by 20+ points (<= 48.5%). Between: report.
- **X:** same as screen v1. FIXES FIT if mean fit gain >= +15 and all 3 seeds positive; HELPS if +5 to +15 with all seeds positive; else NO EFFECT (HURTS if <= -5).
- Wrong if: X fixes fit but the 6-seed confirmation (own marks, written before it runs) does not reproduce it.
