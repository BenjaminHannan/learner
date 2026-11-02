# PREREG k2q4-fix: make sleep work on K2-Horizon-3.7B with a 4-bit base

Thread "Fit sleep on an 8 GB M2" (Ben, 2026-10-25 21:36Z: make 4-bit K2 sleep work; a longer night is acceptable; no bf16 master).
Sealed before any run of the arms below. Small-card / village experiments are not involved; this is the Sleep-B chat-week world only.

## Starting point (addendum 11, Week-2, seed 1, ab_ob_b4_nb, work scale 4, one RTX 5090 each)
- K2 bf16 base: recall C2+C4 96.5, reverse 91.5, diary 84.5, ARC-Easy 89.4 -> 91.0.
- K2 q4 base (`--q4-base`, MLX-affine 4-bit, group 64): recall 86.0 (-10.5, p = 0.0002), reverse 83.5, diary 85.5, ARC 85.6 -> 86.8.
- Earlier on Qwen3.5-2B Week-1 (this thread, Kaggle fp16): q4 recall 45.0 at s=1 and 58.8 at s=2 vs 61.3 normal, so longer nights closed the gap there (one seed).

## Shared setup
Same as the a11 q4 run: `--arm ab_ob_b4_nb --model IFM/K2-Horizon-3.7B --revision 9d280ff742235796925c9fe3cf243dc1beea5c08 --week
backbone/sleep/brain/data/week2.json --seed 1 --arc-base --q4-base`, bsz 16, lr 2e-4, alpha/rank 2. Runs on Ben's PC (RTX 5070 Ti 16 GB, bf16),
`--tok-budget 1024`, or 512 if night 1 runs out of memory (same loss and gradients), `--gen-bs` 32, or 16 on OOM. The GPU differs from a11, so
treat it like a different seed. Primary: recall C2+C4 (weights only, 200 questions), paired exact McNemar against the a11 rows (`paired.py`).

## Arm K1 (run first): longer night, `--budget-scale 8` (2,400 steps a night at the cap, 8 dreams per item, item cap 1,280, REM x8)
- PASS: recall >= 91.5 AND ARC-Easy after >= ARC base - 3 (base read in this run) AND diary >= 79.5 (the bf16 run's 84.5 - 5).
- WRONG (longer nights do not fix 4-bit on K2): recall <= 88.5.
- Between 88.5 and 91.5: partial; go to K2.

## Arm K2 (only if K1 does not pass): bigger add-on at 4x, `--rank 64 --alpha 128`
- PASS / WRONG marks as K1 (WRONG: recall <= 88.5).

## Arm K3 (only if K1 and K2 both miss): a replay-priority boost for facts the 4-bit base handles worse. The code does not exist yet;
it will be sealed as an addendum to this file before it is written.

## Also recorded
Night wall time per night (phase_seconds) and peak GPU memory, so the 8x night length can be scaled to the Mac tiers; reverse,
two-hop, changed-new, routine; gate reverts.
