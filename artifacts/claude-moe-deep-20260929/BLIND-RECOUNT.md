# Blind recount: MoE deep (L8-E64), from raw JSON and PASSMARKS + ADDENDUM-1/2

Not read: VERDICT.json, REPORT-dev.json, the report script, chat or commit messages. All counts are "x of 300" (9x9, learned stop) unless stated.

## Holdout 9x9 counts, k = 1, 4, 16, 64, 256, 1024, 4096, 16384

| arm | counts (x of 300) | F_eq | F_few |
|---|---|---|---|
| MoE seed 0 | 0, 5, 51, 117, 257, 282, 293, 262 | 52.79 | 14.42 |
| MoE seed 1 | 0, 1, 28, 205, 255, 287, 289, 288 | 56.38 | 19.50 |
| loop seed 0 (recorded) | 1, 0, 28, 137, 256, 271, 257, 274 | 51.00 | 13.83 |
| loop seed 1 (recorded) | 1, 0, 3, 190, 262, 236, 284, 255 | 51.29 | 16.17 |
| plain seed 0 (recorded) | 2, 8, 1, 29, 124, 217, 227, 203 | 33.79 | 3.33 |
| plain seed 1 (recorded) | 0, 0, 0, 12, 134, 213, 223, 224 | 33.58 | 1.00 |

MoE fixed-16 reads (fixed_right): s0 0, 4, 45, 115, 255, 279, 290, 249; s1 0, 1, 30, 205, 252, 287, 285, 275.
MoE cap_hits: s0 27, 108, 134, 23, 21, 12, 20, 262; s1 36, 199, 66, 11, 94, 83, 21, 15.

## Comparator
No same-GPU loop control exists (ADDENDUM-1 item 4: untested). L* = 51.29, C_few = 16.17. G1 bar = 61.29.

## G1 per seed
- Seed 0: 52.79 vs 61.29, gap to L* +1.50 (0.38 SD of 3.96). G1 fails.
- Seed 1: 56.38 vs 61.29, gap to L* +5.09 (1.29 SD). G1 fails.

## Stop failures (learned right more than 6 below fixed_right)
None in either seed at any 9x9 rung (learned right is at or above fixed_right at every rung).

## Validity
- V1: seed 0 sums4 200/200, grids5 200/200; seed 1 sums4 200/200, grids5 200/200 (source guard seed 9233000). Pass at lr 1e-3, no retry.
- V2: gradient_check.nonzero_all true in both seeds (76 matrices). Expert liveness 512 of 512 alive.
- Smoke (SMOKE-gpu.json): PASS true, all checks true (logit diff 9.5e-7, stop-prob diff 1.8e-7, routing agreement 1.0, update rel diff 1.6e-4, sleep 1.6e-3). Machine mark satisfied per ADDENDUM-1 item 3.

## Dev 9x9 (adapt.json, x of 300)
s0: 0, 10, 35, 102, 249, 289, 291, 274. s1: 0, 0, 34, 206, 263, 282, 292, 287.
Old kinds (sums4 / grids5 of 200): before s0 200/199, s1 200/200; after k=64 0/0 and after k=16384 0/0 in both seeds (old skills gone under learned stop). Sleep branch (one draw, report only, no claim): see adapt.json "sleep".

## Verdict
- PASS needs G1 in both seeds: no.
- PROVED WRONG needs F_eq <= L* in both seeds: no (52.79 and 56.38 are above 51.29).
- **Verdict word: NOT SHOWN.**
- **R1 F_few word: NOT SEPARABLE.** Few-gaps: s0 14.42 - 16.17 = -1.75; s1 19.50 - 16.17 = +3.33 (need all >= +10.5 or all <= -10.5).

## Discrepancies / rules not applied
- Same-machine loop control not run (comparator is the recorded L*); this is the rule's stated fallback, not a deviation.
- Scaling, attribution, R5, R6 not recounted (out of scope).
- Stop-failure rule applied to 9x9 only.
