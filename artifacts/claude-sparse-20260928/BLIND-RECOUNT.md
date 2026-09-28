# Test D blind recount: the sparse loop (mixture of experts in each loop block)

Written 2026-09-28 by an independent recount agent. I read only the marks (PASSMARKS-D.md, ADDENDUM-D1.md,
RACE-PASSMARKS.md, RACE-ADDENDUM-1.md, ADDENDUM-4.md, PROTOCOL.md) and the raw JSON listed below. I did not read
the race script, any race-*.json, any RESULTS*.md, any other recount or any log. All numbers below come from
one-off Python parsing of:

- `artifacts/claude-sparse-20260928/runs/sparse-s{0,1}/source.json`
- `artifacts/claude-sparse-20260928/eq-runs/sparse-{pre,fresh}-s{0,1}/{adapt,holdout}.json`
- `artifacts/claude-fewex-20260927/eq-runs/{loop,plain}-s{0,1}-pre/{adapt,holdout}.json`

The records are consistent with each other: each file has the expected seed, arm and init. Within each seed, all
four arms share the same `support_sha256` (seed 0 `3efe54c5...`, seed 1 `ad4a726c...`). Every 9x9 holdout rung
has n = 300.

## 1. Source guard (before any maze run)

| Seed | sums4 | grids5 | both >= 190? | gradient_check.nonzero_all | matrix_count | missing_both |
|---|---|---|---|---|---|---|
| 0 | 200 of 200 | 200 of 200 | yes | true | 46 | none |
| 1 | 200 of 200 | 200 of 200 | yes | true | 46 | none |

Source guard **passes in both seeds**. Both practices ran 12,000 steps with guard seed 9233000. The source-selected
fixed depth is 16 in both seeds, the same as the loop's.

## 2. F_eq on the 9x9 holdout (learned stop, eight positive rungs)

F_eq = mean over k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384 of 100 x right / 300.

### Seed 0

| Arm | k=1 | k=4 | k=16 | k=64 | k=256 | k=1,024 | k=4,096 | k=16,384 | F_eq |
|---|---|---|---|---|---|---|---|---|---|
| sparse-pre | 0 of 300 | 5 of 300 | 21 of 300 | 175 of 300 | 277 of 300 | 271 of 300 | 281 of 300 | 287 of 300 | **54.875** |
| sparse-fresh | 0 of 300 | 5 of 300 | 35 of 300 | 122 of 300 | 139 of 300 | 0 of 300 | 44 of 300 | 0 of 300 | 14.375 |
| loop-pre | 1 of 300 | 0 of 300 | 28 of 300 | 137 of 300 | 256 of 300 | 271 of 300 | 257 of 300 | 274 of 300 | 51.000 |
| plain-pre | 2 of 300 | 8 of 300 | 1 of 300 | 29 of 300 | 124 of 300 | 217 of 300 | 227 of 300 | 203 of 300 | 33.792 |

### Seed 1

| Arm | k=1 | k=4 | k=16 | k=64 | k=256 | k=1,024 | k=4,096 | k=16,384 | F_eq |
|---|---|---|---|---|---|---|---|---|---|
| sparse-pre | 0 of 300 | 1 of 300 | 8 of 300 | 139 of 300 | 237 of 300 | 249 of 300 | 188 of 300 | 259 of 300 | **45.042** |
| sparse-fresh | 0 of 300 | 0 of 300 | 36 of 300 | 0 of 300 | 175 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 8.792 |
| loop-pre | 1 of 300 | 0 of 300 | 3 of 300 | 190 of 300 | 262 of 300 | 236 of 300 | 284 of 300 | 255 of 300 | 51.292 |
| plain-pre | 0 of 300 | 0 of 300 | 0 of 300 | 12 of 300 | 134 of 300 | 213 of 300 | 223 of 300 | 224 of 300 | 33.583 |

Cold (k=0) is 0 of 300 for every arm in both seeds.

## 3. Differences (percentage points of F_eq)

| Seed | sparse-pre - loop | sparse-pre - plain | sparse-pre - sparse-fresh |
|---|---|---|---|
| 0 | **+3.875** | +21.083 | +40.500 |
| 1 | **-6.250** | +11.458 | +36.250 |

## 4. Old kinds (right of 200, from adapt.json)

| Seed | Record | sparse-pre sums4 | loop sums4 | gap | sparse-pre grids5 | loop grids5 | gap |
|---|---|---|---|---|---|---|---|
| 0 | old.before | 200 | 200 | 0 | 199 | 199 | 0 |
| 0 | sleep["64"].old | 164 | 149 | +15 | 137 | 99 | +38 |
| 0 | sleep["16384"].old | 146 | 76 | +70 | 121 | 90 | +31 |
| 1 | old.before | 200 | 200 | 0 | 199 | 200 | -1 |
| 1 | sleep["64"].old | 146 | 155 | **-9** | 124 | 86 | +38 |
| 1 | sleep["16384"].old | 79 | 83 | -4 | 112 | 100 | +12 |

(For reference: the plain-pre `old.before` is 200/193 in seed 0 and 200/190 in seed 1. sparse-fresh is 0/0
everywhere. Every arm's `old.after_64` and `old.after_16384`, taken before sleep, is 0 of 200 on both kinds,
including `fixed_right`. This is not a gate, and it is the same for all arms.)

## 5. Gates

Pass marks: "at least 190 of 200", "not more than 6 of 200 below the loop" (3 points), "+5 over plain and fresh",
"+10 over the loop", "within 2% stored weights", and "no stop failure".

| Gate | Seed 0 | Seed 1 |
|---|---|---|
| Source guard V1 (>= 190 of 200 each kind) | pass (200, 200) | pass (200, 200) |
| Source guard V2 (every matrix nonzero gradient) | pass (46/46) | pass (46/46) |
| old.before sums4 >= 190 of 200 | pass (200) | pass (200) |
| old.before grids5 >= 190 of 200 | pass (199) | pass (199) |
| old.before sums4 within 6 of loop | pass (0 below) | pass (0 below) |
| old.before grids5 within 6 of loop | pass (0 below) | pass (1 below) |
| F_eq >= plain + 5 | pass (+21.08) | pass (+11.46) |
| F_eq >= own fresh copy + 5 | pass (+40.50) | pass (+36.25) |
| sleep.64 sums4 within 6 of loop | pass (+15) | **FAIL (9 below: 146 vs 155)** |
| sleep.64 grids5 within 6 of loop | pass (+38) | pass (+38) |
| sleep.16384 sums4 within 6 of loop | pass (+70) | pass (4 below) |
| sleep.16384 grids5 within 6 of loop | pass (+31) | pass (+12) |
| Stored weights within 2% of loop | pass (1,645,198 vs 1,645,726, -0.032%) | pass (same) |
| Learned stop: cap 48, same fixed depth (16), no 9x9 stop failure | pass | pass (see ambiguity c) |
| **F_eq >= loop + 10** | **FAIL (+3.875)** | **FAIL (-6.250)** |

**Proved-wrong clause.**
- "F_eq no higher than the loop in both seeds." This does **not** hold, because seed 0 is +3.875 above the loop.
- "A maze gain only by breaking an old-kind gate." This does **not** hold. Seed 0 has the maze gain and breaks no
  old-kind gate. Seed 1 breaks an old-kind gate (sleep.64 sums4) but has no F_eq gain.

**Verdict: NOT PROMOTED.** The failing gates are:
- the +10 over the loop, in both seeds (+3.875 and -6.250);
- in seed 1, the sleep.64 sums4 gate (146 of 200 vs the loop's 155 of 200, 9 below; the limit is 6).

## 6. Stored weights

Sparse is 1,645,198 and the loop is 1,645,726. The difference is -528 (-0.032%), within 2%. Both source.json and
adapt.json record the same figure in `weights` and `persistent_coefficients`. Plain has 1,619,965, for reference.

## 7. Report only: 9x9 k=64 reaching 150 of 300 (sparse-pre, holdout)

| Seed | k=64 | reached 150? | E50 (smallest rung >= 150 of 300) |
|---|---|---|---|
| 0 | 175 of 300 | yes | k = 64 |
| 1 | 139 of 300 | no | k = 256 |

For comparison, the loop's k=64 is 137 of 300 in seed 0 (E50 k=256) and 190 of 300 in seed 1 (E50 k=64).

## Ambiguities and whether they change the verdict

a. **"Within three points" vs "not more than 6 of 200".** These are the same threshold (3 pp of 200 = 6). The
   seed-1 sleep.64 sums4 gap is 9 (4.5 pp), so it fails under either wording. The seed-1 sleep.16384 sums4 gap is
   4 (2 pp), so it passes under either. No change.

b. **The proved-wrong "maze gain only by breaking an old-kind gate".** On the pre-set reading (F_eq, each seed
   alone), no seed has both a gain and a broken old gate, so the verdict is not REJECTED. Pooling the seeds does not
   change this: the mean F_eq is 49.96 for sparse vs 51.15 for the loop, so there is no pooled gain, and the first
   clause still needs both seeds. A strained reading would count a per-rung gain in seed 1 together with the broken
   sleep.64 sums4 gate. Seed 1 is higher than the loop at k=4 (1 vs 0), k=16 (8 vs 3), k=1,024 (249 vs 236) and
   k=16,384 (259 vs 255). Under that reading the verdict would become REJECTED. The marks define every maze
   comparison through F_eq, so I do not adopt it.

c. **Stop failures on the secondary panels.** The marks say the check is "reported for every rung". Read that way,
   it is a report, not a promotion gate. On the 9x9 panel (dev and holdout) no arm in either seed has a stop failure.
   On the 7x7 panel, one maze is 2.08 pp (holdout, n=48) or 4.17 pp (dev, n=24), so a single maze trips the
   2-point rule:
   - sparse-pre seed 1: holdout k=16 (5 vs fixed 6 of 48) and dev k=4,096 (19 vs 21 of 24);
   - loop-pre seed 0: holdout k=1 (2 vs 3) and k=1,024 (44 vs 46), and dev k=64 (12 vs 14);
   - loop-pre seed 1: holdout k=64 (35 vs 36) and k=4,096 (46 vs 47).

   If stop failures on any panel were a gate, seed 1 would gain one more failing gate. The verdict stays NOT
   PROMOTED.

d. **Precondition.** Test D applies only after the equal-practice baseline passes V1 to V3 (EQ-DEV-GATE.json PASS),
   and dev must run before holdout. I was not allowed to read those files, so I cannot confirm either. The baseline
   holdout.json files exist, and ADDENDUM-D1.md says the harness's `holdout` command refuses unless the gate passed.
   If the gate had not passed, the result would be INCONCLUSIVE instead.

e. **Old-kind gates after maze training but before sleep** (`old.after_64`, `old.after_16384`). These are not named
   in the marks. They are 0 of 200 for every arm, so no reading that includes them changes anything paired against
   the loop.

**Bottom line:** the source guard passes and the weight budget passes. The +10 over the loop fails in both seeds:
+3.9 pp in seed 0 and -6.3 pp in seed 1. Seed 1 also fails the k=64 sleep sums gate (9 of 200 below the loop).
The proved-wrong clause does not hold, so the verdict is **NOT PROMOTED**, not REJECTED.
