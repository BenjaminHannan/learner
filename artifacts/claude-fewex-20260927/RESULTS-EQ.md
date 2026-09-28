# Equal-practice few-example ruler: usable

Written 2026-09-28 05:07:26 UTC. **Shown:** V1, V2 and V3 pass on the revised eight-rung ladder. The unopened maze holdout was then scored once for each of the eight arm/seed runs. The new ruler is usable under its registered V3 rule. Equal practice materially changed the few-example curve; the results below are descriptive baseline measurements, not design-race verdicts.

Seal commits: `bcb64da89` (ADDENDUM-4 and RACE-ADDENDUM-1, before any new maze score); `db814a8fb` (new harness and sampling self-check, before scores); `e82d00d38` (all eight dev JSONs and V3 decision, before reading holdout scores). The earlier ladder was INCONCLUSIVE at `c0d023346`; this addendum was made after its dev scores, and its holdout remained unopened until this revised run passed V3. The race addendum replaces `F_all` with `F_eq` in all race marks without changing thresholds. No design result is judged here.

## Validity and exposure

The qualified source nets are the existing matched 12,000-step checkpoints; no source net was retrained. V1 uses the qualified fresh source guard, V2 its fp32 gradient check, and V3 the new dev ladder. Dev means the panel used for the validity decision; holdout means the one-time final panel.

| Check | Result | Raw evidence |
|---|---|---|
| V1 | PASS | All four qualified sources pass both old-kind guards, each at least 190 of 200. |
| V2 | PASS | All two-dimensional matrices have nonzero fp32 gradients: loop 16 of 16; plain 51 of 51, in both seeds. |
| V3 | PASS | All eight runs have at least 3 of 8 dev 9×9 rungs strictly between 30 of 300 and 270 of 300. |

| Source net | Seed | Fresh sums | Fresh grids | Live matrices | Weights / persistent coefficients |
|---|---:|---:|---:|---:|---:|
| loop | 0 | 200 of 200 | 200 of 200 | 16 of 16 | 1,645,726 / 1,645,726 |
| loop | 1 | 200 of 200 | 200 of 200 | 16 of 16 | 1,645,726 / 1,645,726 |
| plain | 0 | 200 of 200 | 195 of 200 | 51 of 51 | 1,619,965 / 1,619,965 |
| plain | 1 | 200 of 200 | 191 of 200 | 51 of 51 | 1,619,965 / 1,619,965 |

| Dev arm | Seed | Intermediate positive rungs | Number |
|---|---:|---|---:|
| practised loop | 0 | 64, 256, 4096 | 3 of 8 |
| fresh loop | 0 | 16, 64, 256, 1024, 4096, 16384 | 6 of 8 |
| practised plain | 0 | 256, 1024, 4096, 16384 | 4 of 8 |
| fresh plain | 0 | 256, 1024, 4096, 16384 | 4 of 8 |
| practised loop | 1 | 64, 1024, 16384 | 3 of 8 |
| fresh loop | 1 | 16, 64, 256, 4096 | 4 of 8 |
| practised plain | 1 | 256, 1024, 4096, 16384 | 4 of 8 |
| fresh plain | 1 | 256, 1024, 4096, 16384 | 4 of 8 |

Every seed pool has 16,384 of 16,384 unique 9×9 layouts and 0 of 16,384 overlapping panel layouts. Each seed pool is identical across the four paired arms (SHA-256 seed 0: `3efe54c5218d83ebc7b26e11899f9a2cd4dbbeb013521ccc69ef58dc84cabe2d`; seed 1: `ad4a726c50a6e26a72339ecc046cc978d03068877e38e50042a93899b462677e`). Dev panels contain 24 of 24, 300 of 300 and 300 of 300 distinct layouts at 7×7, 9×9 and 11×11; holdout panels contain 48 of 48, 300 of 300 and 300 of 300. Each positive rung trained from a clean starting copy for exactly 512 batches of 32 and 2,048 optimizer updates. Visits per selected layout at k=1/4/16/64/256/1,024/4,096/16,384 were 16,384/4,096/1,024/256/64/16/4/1, respectively. The new 2,048-update amount was fixed before any new score.

## Main 9×9 scores

`F_eq` is the unweighted mean accuracy over the eight positive holdout rungs. `E50` is the first rung at or above 150 of 300, report-only; the curves can be nonmonotonic. Cold k=0 is reported in the detailed table. All rung entries below are correct counts **of 300**.

| Arm | Seed | 1 | 4 | 16 | 64 | 256 | 1,024 | 4,096 | 16,384 | F_eq | E50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| practised loop | 0 | 1 of 300 | 0 of 300 | 28 of 300 | 137 of 300 | 256 of 300 | 271 of 300 | 257 of 300 | 274 of 300 | 51.00% | 256 |
| fresh loop | 0 | 0 of 300 | 13 of 300 | 34 of 300 | 49 of 300 | 144 of 300 | 67 of 300 | 85 of 300 | 104 of 300 | 20.67% | not reached |
| practised plain | 0 | 2 of 300 | 8 of 300 | 1 of 300 | 29 of 300 | 124 of 300 | 217 of 300 | 227 of 300 | 203 of 300 | 33.79% | 1024 |
| fresh plain | 0 | 0 of 300 | 3 of 300 | 2 of 300 | 24 of 300 | 138 of 300 | 123 of 300 | 107 of 300 | 142 of 300 | 22.46% | not reached |
| practised loop | 1 | 1 of 300 | 0 of 300 | 3 of 300 | 190 of 300 | 262 of 300 | 236 of 300 | 284 of 300 | 255 of 300 | 51.29% | 64 |
| fresh loop | 1 | 0 of 300 | 1 of 300 | 36 of 300 | 166 of 300 | 167 of 300 | 0 of 300 | 128 of 300 | 18 of 300 | 21.50% | 64 |
| practised plain | 1 | 0 of 300 | 0 of 300 | 0 of 300 | 12 of 300 | 134 of 300 | 213 of 300 | 223 of 300 | 224 of 300 | 33.58% | 1024 |
| fresh plain | 1 | 0 of 300 | 1 of 300 | 11 of 300 | 25 of 300 | 120 of 300 | 142 of 300 | 149 of 300 | 152 of 300 | 25.00% | 16384 |

The full dev 9×9 curves are below for comparison; all entries are counts **of 300** and did not set any training choice after the addendum.

| Arm | Seed | 1 | 4 | 16 | 64 | 256 | 1,024 | 4,096 | 16,384 | Dev F_eq |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| practised loop | 0 | 2 of 300 | 0 of 300 | 21 of 300 | 126 of 300 | 263 of 300 | 275 of 300 | 256 of 300 | 286 of 300 | 51.21% |
| fresh loop | 0 | 0 of 300 | 15 of 300 | 33 of 300 | 51 of 300 | 130 of 300 | 66 of 300 | 69 of 300 | 109 of 300 | 19.71% |
| practised plain | 0 | 1 of 300 | 4 of 300 | 1 of 300 | 29 of 300 | 127 of 300 | 216 of 300 | 229 of 300 | 210 of 300 | 34.04% |
| fresh plain | 0 | 0 of 300 | 0 of 300 | 8 of 300 | 21 of 300 | 125 of 300 | 127 of 300 | 108 of 300 | 129 of 300 | 21.58% |
| practised loop | 1 | 0 of 300 | 0 of 300 | 4 of 300 | 173 of 300 | 277 of 300 | 233 of 300 | 292 of 300 | 261 of 300 | 51.67% |
| fresh loop | 1 | 0 of 300 | 1 of 300 | 39 of 300 | 164 of 300 | 161 of 300 | 0 of 300 | 116 of 300 | 24 of 300 | 21.04% |
| practised plain | 1 | 0 of 300 | 0 of 300 | 1 of 300 | 14 of 300 | 118 of 300 | 207 of 300 | 228 of 300 | 215 of 300 | 32.62% |
| fresh plain | 1 | 0 of 300 | 0 of 300 | 6 of 300 | 26 of 300 | 119 of 300 | 143 of 300 | 144 of 300 | 131 of 300 | 23.71% |

**Shown, paired seed 0:** practised loop F_eq 51.00%, fresh loop 20.67% (difference +30.33 points), and practised plain 33.79% (loop difference +17.21 points).
**Shown, paired seed 1:** practised loop F_eq 51.29%, fresh loop 21.50% (difference +29.79 points), and practised plain 33.58% (loop difference +17.71 points).

**Shown:** the practised loop first reaches 150 of 300 at k=256 in seed 0 and k=64 in seed 1. Fresh loop does not reach it in seed 0, but reaches it at k=64 in seed 1 (then falls below at later rungs). Practised plain first reaches it at k=1,024 in both seeds. **Suggested:** prior source practice raises average maze transfer, and the recurrent architecture helps at this budget. **Untested:** whether either effect survives new seeds, maze families or a causal architecture ablation. The strong nonmonotonicity means E50 alone does not represent stable learning.

## Detailed one-time holdout scores

Each row is an independently trained positive rung or a separate sleep copy, except cold k=0. The 7×7 count is of 48; 9×9 and 11×11 counts, fixed-depth 9×9 counts and cap hits are of 300. The loop fixed depth was 16, chosen on source dev; plain depth was 1. A stop failure requires learned-stop accuracy more than two points (more than 6 of 300) below fixed-depth accuracy.

| Arm | Seed | Stage | 7×7 | 9×9 | 11×11 | Fixed 9×9 | Mean rounds 9×9 | Cap hits 9×9 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| practised loop | 0 | 0 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 |
| practised loop | 0 | 1 | 2 of 48 | 1 of 300 | 0 of 300 | 1 of 300 | 48.0 | 300 of 300 |
| practised loop | 0 | 4 | 3 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 |
| practised loop | 0 | 16 | 14 of 48 | 28 of 300 | 5 of 300 | 28 of 300 | 48.0 | 300 of 300 |
| practised loop | 0 | 64 | 22 of 48 | 137 of 300 | 71 of 300 | 136 of 300 | 48.0 | 300 of 300 |
| practised loop | 0 | 256 | 48 of 48 | 256 of 300 | 157 of 300 | 245 of 300 | 48.0 | 300 of 300 |
| practised loop | 0 | 1024 | 44 of 48 | 271 of 300 | 190 of 300 | 265 of 300 | 48.0 | 300 of 300 |
| practised loop | 0 | 4096 | 47 of 48 | 257 of 300 | 124 of 300 | 243 of 300 | 48.0 | 300 of 300 |
| practised loop | 0 | 16384 | 48 of 48 | 274 of 300 | 200 of 300 | 270 of 300 | 31.9 | 163 of 300 |
| practised loop | 0 | sleep64 | 31 of 48 | 156 of 300 | 74 of 300 | 153 of 300 | 48.0 | 300 of 300 |
| practised loop | 0 | sleep16384 | 48 of 48 | 289 of 300 | 222 of 300 | 285 of 300 | 10.0 | 8 of 300 |
| fresh loop | 0 | 0 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 3.0 | 0 of 300 |
| fresh loop | 0 | 1 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 |
| fresh loop | 0 | 4 | 4 of 48 | 13 of 300 | 7 of 300 | 13 of 300 | 21.1 | 63 of 300 |
| fresh loop | 0 | 16 | 13 of 48 | 34 of 300 | 17 of 300 | 35 of 300 | 32.2 | 168 of 300 |
| fresh loop | 0 | 64 | 19 of 48 | 49 of 300 | 25 of 300 | 44 of 300 | 47.9 | 299 of 300 |
| fresh loop | 0 | 256 | 30 of 48 | 144 of 300 | 75 of 300 | 144 of 300 | 39.4 | 223 of 300 |
| fresh loop | 0 | 1024 | 18 of 48 | 67 of 300 | 27 of 300 | 71 of 300 | 48.0 | 300 of 300 |
| fresh loop | 0 | 4096 | 17 of 48 | 85 of 300 | 41 of 300 | 72 of 300 | 9.8 | 8 of 300 |
| fresh loop | 0 | 16384 | 27 of 48 | 104 of 300 | 47 of 300 | 99 of 300 | 48.0 | 300 of 300 |
| fresh loop | 0 | sleep64 | 23 of 48 | 67 of 300 | 33 of 300 | 66 of 300 | 48.0 | 300 of 300 |
| fresh loop | 0 | sleep16384 | 33 of 48 | 85 of 300 | 15 of 300 | 77 of 300 | 48.0 | 300 of 300 |
| practised plain | 0 | 0 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 |
| practised plain | 0 | 1 | 1 of 48 | 2 of 300 | 0 of 300 | 2 of 300 | 1.0 | 0 of 300 |
| practised plain | 0 | 4 | 3 of 48 | 8 of 300 | 1 of 300 | 8 of 300 | 1.0 | 0 of 300 |
| practised plain | 0 | 16 | 2 of 48 | 1 of 300 | 0 of 300 | 1 of 300 | 1.0 | 0 of 300 |
| practised plain | 0 | 64 | 12 of 48 | 29 of 300 | 5 of 300 | 29 of 300 | 1.0 | 0 of 300 |
| practised plain | 0 | 256 | 26 of 48 | 124 of 300 | 29 of 300 | 124 of 300 | 1.0 | 0 of 300 |
| practised plain | 0 | 1024 | 47 of 48 | 217 of 300 | 54 of 300 | 217 of 300 | 1.0 | 0 of 300 |
| practised plain | 0 | 4096 | 45 of 48 | 227 of 300 | 65 of 300 | 227 of 300 | 1.0 | 0 of 300 |
| practised plain | 0 | 16384 | 42 of 48 | 203 of 300 | 68 of 300 | 203 of 300 | 1.0 | 0 of 300 |
| practised plain | 0 | sleep64 | 10 of 48 | 23 of 300 | 2 of 300 | 23 of 300 | 1.0 | 0 of 300 |
| practised plain | 0 | sleep16384 | 37 of 48 | 184 of 300 | 51 of 300 | 184 of 300 | 1.0 | 0 of 300 |
| fresh plain | 0 | 0 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 |
| fresh plain | 0 | 1 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 |
| fresh plain | 0 | 4 | 0 of 48 | 3 of 300 | 0 of 300 | 3 of 300 | 1.0 | 0 of 300 |
| fresh plain | 0 | 16 | 4 of 48 | 2 of 300 | 0 of 300 | 2 of 300 | 1.0 | 0 of 300 |
| fresh plain | 0 | 64 | 5 of 48 | 24 of 300 | 6 of 300 | 24 of 300 | 1.0 | 0 of 300 |
| fresh plain | 0 | 256 | 34 of 48 | 138 of 300 | 39 of 300 | 138 of 300 | 1.0 | 0 of 300 |
| fresh plain | 0 | 1024 | 28 of 48 | 123 of 300 | 46 of 300 | 123 of 300 | 1.0 | 0 of 300 |
| fresh plain | 0 | 4096 | 36 of 48 | 107 of 300 | 17 of 300 | 107 of 300 | 1.0 | 0 of 300 |
| fresh plain | 0 | 16384 | 35 of 48 | 142 of 300 | 54 of 300 | 142 of 300 | 1.0 | 0 of 300 |
| fresh plain | 0 | sleep64 | 7 of 48 | 20 of 300 | 4 of 300 | 20 of 300 | 1.0 | 0 of 300 |
| fresh plain | 0 | sleep16384 | 39 of 48 | 117 of 300 | 6 of 300 | 117 of 300 | 1.0 | 0 of 300 |
| practised loop | 1 | 0 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 |
| practised loop | 1 | 1 | 0 of 48 | 1 of 300 | 0 of 300 | 1 of 300 | 48.0 | 300 of 300 |
| practised loop | 1 | 4 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 |
| practised loop | 1 | 16 | 4 of 48 | 3 of 300 | 1 of 300 | 3 of 300 | 13.4 | 23 of 300 |
| practised loop | 1 | 64 | 35 of 48 | 190 of 300 | 109 of 300 | 185 of 300 | 43.3 | 262 of 300 |
| practised loop | 1 | 256 | 47 of 48 | 262 of 300 | 182 of 300 | 257 of 300 | 48.0 | 300 of 300 |
| practised loop | 1 | 1024 | 46 of 48 | 236 of 300 | 176 of 300 | 227 of 300 | 20.6 | 71 of 300 |
| practised loop | 1 | 4096 | 46 of 48 | 284 of 300 | 193 of 300 | 283 of 300 | 34.8 | 196 of 300 |
| practised loop | 1 | 16384 | 47 of 48 | 255 of 300 | 144 of 300 | 253 of 300 | 33.1 | 177 of 300 |
| practised loop | 1 | sleep64 | 31 of 48 | 146 of 300 | 73 of 300 | 145 of 300 | 33.1 | 178 of 300 |
| practised loop | 1 | sleep16384 | 48 of 48 | 283 of 300 | 241 of 300 | 284 of 300 | 27.1 | 134 of 300 |
| fresh loop | 1 | 0 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 3.0 | 0 of 300 |
| fresh loop | 1 | 1 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 48.0 | 300 of 300 |
| fresh loop | 1 | 4 | 1 of 48 | 1 of 300 | 0 of 300 | 1 of 300 | 43.8 | 262 of 300 |
| fresh loop | 1 | 16 | 9 of 48 | 36 of 300 | 23 of 300 | 34 of 300 | 43.3 | 252 of 300 |
| fresh loop | 1 | 64 | 31 of 48 | 166 of 300 | 85 of 300 | 168 of 300 | 13.0 | 5 of 300 |
| fresh loop | 1 | 256 | 36 of 48 | 167 of 300 | 72 of 300 | 165 of 300 | 11.9 | 1 of 300 |
| fresh loop | 1 | 1024 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 3.0 | 0 of 300 |
| fresh loop | 1 | 4096 | 36 of 48 | 128 of 300 | 63 of 300 | 121 of 300 | 15.6 | 17 of 300 |
| fresh loop | 1 | 16384 | 22 of 48 | 18 of 300 | 1 of 300 | 19 of 300 | 13.3 | 0 of 300 |
| fresh loop | 1 | sleep64 | 33 of 48 | 142 of 300 | 59 of 300 | 144 of 300 | 19.3 | 57 of 300 |
| fresh loop | 1 | sleep16384 | 41 of 48 | 173 of 300 | 107 of 300 | 183 of 300 | 21.6 | 70 of 300 |
| practised plain | 1 | 0 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 |
| practised plain | 1 | 1 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 |
| practised plain | 1 | 4 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 |
| practised plain | 1 | 16 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 |
| practised plain | 1 | 64 | 8 of 48 | 12 of 300 | 5 of 300 | 12 of 300 | 1.0 | 0 of 300 |
| practised plain | 1 | 256 | 37 of 48 | 134 of 300 | 37 of 300 | 134 of 300 | 1.0 | 0 of 300 |
| practised plain | 1 | 1024 | 41 of 48 | 213 of 300 | 103 of 300 | 213 of 300 | 1.0 | 0 of 300 |
| practised plain | 1 | 4096 | 47 of 48 | 223 of 300 | 79 of 300 | 223 of 300 | 1.0 | 0 of 300 |
| practised plain | 1 | 16384 | 40 of 48 | 224 of 300 | 92 of 300 | 224 of 300 | 1.0 | 0 of 300 |
| practised plain | 1 | sleep64 | 8 of 48 | 7 of 300 | 2 of 300 | 7 of 300 | 1.0 | 0 of 300 |
| practised plain | 1 | sleep16384 | 48 of 48 | 238 of 300 | 59 of 300 | 238 of 300 | 1.0 | 0 of 300 |
| fresh plain | 1 | 0 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 |
| fresh plain | 1 | 1 | 0 of 48 | 0 of 300 | 0 of 300 | 0 of 300 | 1.0 | 0 of 300 |
| fresh plain | 1 | 4 | 0 of 48 | 1 of 300 | 0 of 300 | 1 of 300 | 1.0 | 0 of 300 |
| fresh plain | 1 | 16 | 2 of 48 | 11 of 300 | 1 of 300 | 11 of 300 | 1.0 | 0 of 300 |
| fresh plain | 1 | 64 | 12 of 48 | 25 of 300 | 10 of 300 | 25 of 300 | 1.0 | 0 of 300 |
| fresh plain | 1 | 256 | 34 of 48 | 120 of 300 | 43 of 300 | 120 of 300 | 1.0 | 0 of 300 |
| fresh plain | 1 | 1024 | 26 of 48 | 142 of 300 | 49 of 300 | 142 of 300 | 1.0 | 0 of 300 |
| fresh plain | 1 | 4096 | 41 of 48 | 149 of 300 | 47 of 300 | 149 of 300 | 1.0 | 0 of 300 |
| fresh plain | 1 | 16384 | 37 of 48 | 152 of 300 | 30 of 300 | 152 of 300 | 1.0 | 0 of 300 |
| fresh plain | 1 | sleep64 | 12 of 48 | 16 of 300 | 2 of 300 | 16 of 300 | 1.0 | 0 of 300 |
| fresh plain | 1 | sleep16384 | 41 of 48 | 191 of 300 | 77 of 300 | 191 of 300 | 1.0 | 0 of 300 |

**Shown:** no positive-rung stop failure occurred. One sleep snapshot failed the stop check: fresh loop seed 1 after k=16,384 sleep had learned 173 of 300 versus fixed-depth 183 of 300, a 10 of 300 gap (3.33 percentage points).

## Old kinds and sleep

Each old-kind cell is a count **of 200** on the fixed old panel, separate from the fresh V1 guard. `D = before − after sleep`, in percentage points, so negative D means improvement. Each sleep branch used 512 optimizer updates with the unchanged 4 sums + 4 grids + 8 branch mazes weighted recipe and a common replay allowance of 128 stored sums and 128 stored grids. Every maze rung has 2,048 updates; sleep adds 512 more to its copy.

| Arm | Seed | Old kind | Before | After 64 | Sleep 64 | D64 | After 16,384 | Sleep 16,384 | D16,384 |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| practised loop | 0 | sums4 | 200 of 200 | 0 of 200 | 149 of 200 | +25.5 | 0 of 200 | 76 of 200 | +62.0 |
| practised loop | 0 | grids5 | 199 of 200 | 0 of 200 | 99 of 200 | +50.0 | 0 of 200 | 90 of 200 | +54.5 |
| fresh loop | 0 | sums4 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 0 of 200 | +0.0 |
| fresh loop | 0 | grids5 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 0 of 200 | +0.0 |
| practised plain | 0 | sums4 | 200 of 200 | 0 of 200 | 198 of 200 | +1.0 | 0 of 200 | 190 of 200 | +5.0 |
| practised plain | 0 | grids5 | 193 of 200 | 0 of 200 | 133 of 200 | +30.0 | 0 of 200 | 104 of 200 | +44.5 |
| fresh plain | 0 | sums4 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 1 of 200 | -0.5 |
| fresh plain | 0 | grids5 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 0 of 200 | +0.0 |
| practised loop | 1 | sums4 | 200 of 200 | 0 of 200 | 155 of 200 | +22.5 | 0 of 200 | 83 of 200 | +58.5 |
| practised loop | 1 | grids5 | 200 of 200 | 0 of 200 | 86 of 200 | +57.0 | 0 of 200 | 100 of 200 | +50.0 |
| fresh loop | 1 | sums4 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 0 of 200 | +0.0 |
| fresh loop | 1 | grids5 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 0 of 200 | +0.0 |
| practised plain | 1 | sums4 | 200 of 200 | 0 of 200 | 196 of 200 | +2.0 | 0 of 200 | 167 of 200 | +16.5 |
| practised plain | 1 | grids5 | 190 of 200 | 0 of 200 | 110 of 200 | +40.0 | 0 of 200 | 98 of 200 | +46.0 |
| fresh plain | 1 | sums4 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 0 of 200 | +0.0 |
| fresh plain | 1 | grids5 | 0 of 200 | 0 of 200 | 0 of 200 | +0.0 | 0 of 200 | 0 of 200 | +0.0 |

**Shown:** maze-only adaptation erased the old panel scores in every arm at k=64 and k=16,384 (0 of 200 each). Sleep recovered some old performance but did not preserve the practised loop’s original scores: after k=64 sleep, its sums were 149 and 155 of 200 and grids 99 and 86 of 200; after k=16,384 sleep, sums were 76 and 83 of 200 and grids 90 and 100 of 200. **Suggested:** the fixed sleep recipe is insufficient under 2,048 maze updates. **Untested:** whether a different sleep recipe would retain both kinds without harming maze transfer; this run did not tune it.

## Compute, audit and limits

| Arm | Seed | Start | Learning rate | Weights / persistent coefficients | Dev adaptation time |
|---|---:|---|---:|---:|---:|
| loop | 0 | practised | 0.001 | 1,645,726 / 1,645,726 | 169.1 min |
| loop | 0 | fresh | 0.001 | 1,645,726 / 1,645,726 | 168.9 min |
| plain | 0 | practised | 0.0005 | 1,619,965 / 1,619,965 | 119.8 min |
| plain | 0 | fresh | 0.0005 | 1,619,965 / 1,619,965 | 119.8 min |
| loop | 1 | practised | 0.001 | 1,645,726 / 1,645,726 | 168.7 min |
| loop | 1 | fresh | 0.001 | 1,645,726 / 1,645,726 | 168.8 min |
| plain | 1 | practised | 0.0005 | 1,619,965 / 1,619,965 | 119.8 min |
| plain | 1 | fresh | 0.0005 | 1,619,965 / 1,619,965 | 119.9 min |

**Shown:** the eight CPU dev jobs ran concurrently; longest was 169.2 minutes, with plain jobs about 119.8 minutes. The one-time holdout completed by 05:04 UTC after the 04:54 UTC dev decision. The new baseline took about three hours of elapsed wall time and $0 in rental charges. The prior 12,000-step source training is reused, not charged to this rerun. The raw old replay allowance was 256 stored examples per arm; each seed also had a 16,384-example support pool. Exact raw-memory bytes were not recorded, so no byte-level memory comparison is claimed.

The raw records are `eq-runs/*/adapt.json`, `eq-runs/*/holdout.json`, `EQ-DEV-GATE.json` and the four `runs/qual-*/source.json` files, with SHA-256 digests in `SHA256-EQ-RAW.txt`. Checkpoints remain local for audit and are not pushed as model weights. The independent blind recount in `BLIND-RECOUNT-EQ.md` matched V1–V3, the holdout F_eq/E50 arithmetic, panel denominators, support hashes and update metadata; it found no numerical discrepancy. It calls the after-sleep minus pre-sleep count a **sleep gain**; this report's `D` uses the original protocol's old-before minus after-sleep percentage-point definition. Its permitted files lacked the original stop-failure formula; this report applies the original protocol's greater-than-two-point rule. The recount noted that raw JSON names a Desktop source path: the requested Downloads workspace is a symlink to that same Desktop checkout, as verified by `realpath`. The relation, patch and sparse-loop design comparisons remain untested by this baseline.
