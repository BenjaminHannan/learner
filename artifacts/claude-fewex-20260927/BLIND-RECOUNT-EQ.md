# Blind recount: equal-practice few-example ruler

Recounted 2026-09-28 05:09:31 UTC (from `date -u`).

## Scope and arithmetic

**Shown:** This recount uses only `PASSMARKS.md`, `ADDENDUM-4.md`, `RACE-ADDENDUM-1.md`, `EQ-DEV-GATE.json`, the four permitted `source.json` files, and the 16 permitted equal-practice `adapt.json`/`holdout.json` files. It recomputes recorded counts and metadata; it does not execute scoring, training, or a design race. `pre` means source-trained/practiced; `fresh` means fresh start. Every 9×9 rung has 300 items. `F_eq = (sum of the eight positive-rung right counts)/24` percentage points; k=0 and sleep scores are excluded. E50 is the first positive holdout rung with at least 150 of 300.

## V1, V2, V3 validity

| Qualified source | Sums4 | Grids5 | Two-dimensional matrices with nonzero gradient on ≥1 batch | Missing on both |
|---|---:|---:|---:|---:|
| loop-s0 | 200 of 200 | 200 of 200 | 16 of 16 | 0 of 16 |
| plain-s0 | 200 of 200 | 195 of 200 | 51 of 51 | 0 of 51 |
| loop-s1 | 200 of 200 | 200 of 200 | 16 of 16 | 0 of 16 |
| plain-s1 | 200 of 200 | 191 of 200 | 51 of 51 | 0 of 51 |

**Shown:** V1 passes for 4 of 4 source models: every kind is at least 190 of 200. V2 passes for 4 of 4 recorded one-step checks: 16 of 16 loop matrices and 51 of 51 plain matrices per seed have a nonzero gradient on at least one old-kind batch; the missing-name lists are empty. These are recorded check results, not a rerun of gradients.

V3 counts below are dev 9×9 correct counts, each written as “x of 300” in rung order. A middle rung has 31 to 269 correct of 300, strictly between 10% and 90%.

| Arm / seed | 1 | 4 | 16 | 64 | 256 | 1,024 | 4,096 | 16,384 | Middle rungs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| loop-s0-pre | 2 of 300 | 0 of 300 | 21 of 300 | 126 of 300 | 263 of 300 | 275 of 300 | 256 of 300 | 286 of 300 | 3 of 8 |
| loop-s0-fresh | 0 of 300 | 15 of 300 | 33 of 300 | 51 of 300 | 130 of 300 | 66 of 300 | 69 of 300 | 109 of 300 | 6 of 8 |
| plain-s0-pre | 1 of 300 | 4 of 300 | 1 of 300 | 29 of 300 | 127 of 300 | 216 of 300 | 229 of 300 | 210 of 300 | 4 of 8 |
| plain-s0-fresh | 0 of 300 | 0 of 300 | 8 of 300 | 21 of 300 | 125 of 300 | 127 of 300 | 108 of 300 | 129 of 300 | 4 of 8 |
| loop-s1-pre | 0 of 300 | 0 of 300 | 4 of 300 | 173 of 300 | 277 of 300 | 233 of 300 | 292 of 300 | 261 of 300 | 3 of 8 |
| loop-s1-fresh | 0 of 300 | 1 of 300 | 39 of 300 | 164 of 300 | 161 of 300 | 0 of 300 | 116 of 300 | 24 of 300 | 4 of 8 |
| plain-s1-pre | 0 of 300 | 0 of 300 | 1 of 300 | 14 of 300 | 118 of 300 | 207 of 300 | 228 of 300 | 215 of 300 | 4 of 8 |
| plain-s1-fresh | 0 of 300 | 0 of 300 | 6 of 300 | 26 of 300 | 119 of 300 | 143 of 300 | 144 of 300 | 131 of 300 | 4 of 8 |

**Shown:** V3 passes for 8 of 8 arm-seed pairs (each has at least 3 of 8 middle rungs), and the independently reconstructed right-count maps and middle-rung lists match `EQ-DEV-GATE.json` for 8 of 8. The recorded gate verdict `PASS` agrees with V1–V3. The holdout results are therefore eligible under the permitted marks.

## Holdout 9×9 ruler

Each exact count is written as “x of 300”; k=0 is cold and excluded from F_eq.

| Arm / seed | k=0 | 1 | 4 | 16 | 64 | 256 | 1,024 | 4,096 | 16,384 | F_eq | E50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| loop-s0-pre | 0 of 300 | 1 of 300 | 0 of 300 | 28 of 300 | 137 of 300 | 256 of 300 | 271 of 300 | 257 of 300 | 274 of 300 | 51.00% (1224 of 2,400) | 256 |
| loop-s0-fresh | 0 of 300 | 0 of 300 | 13 of 300 | 34 of 300 | 49 of 300 | 144 of 300 | 67 of 300 | 85 of 300 | 104 of 300 | 20.67% (496 of 2,400) | not reached |
| plain-s0-pre | 0 of 300 | 2 of 300 | 8 of 300 | 1 of 300 | 29 of 300 | 124 of 300 | 217 of 300 | 227 of 300 | 203 of 300 | 33.79% (811 of 2,400) | 1024 |
| plain-s0-fresh | 0 of 300 | 0 of 300 | 3 of 300 | 2 of 300 | 24 of 300 | 138 of 300 | 123 of 300 | 107 of 300 | 142 of 300 | 22.46% (539 of 2,400) | not reached |
| loop-s1-pre | 0 of 300 | 1 of 300 | 0 of 300 | 3 of 300 | 190 of 300 | 262 of 300 | 236 of 300 | 284 of 300 | 255 of 300 | 51.29% (1231 of 2,400) | 64 |
| loop-s1-fresh | 0 of 300 | 0 of 300 | 1 of 300 | 36 of 300 | 166 of 300 | 167 of 300 | 0 of 300 | 128 of 300 | 18 of 300 | 21.50% (516 of 2,400) | 64 |
| plain-s1-pre | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 12 of 300 | 134 of 300 | 213 of 300 | 223 of 300 | 224 of 300 | 33.58% (806 of 2,400) | 1024 |
| plain-s1-fresh | 0 of 300 | 0 of 300 | 1 of 300 | 11 of 300 | 25 of 300 | 120 of 300 | 142 of 300 | 149 of 300 | 152 of 300 | 25.00% (600 of 2,400) | 16384 |

**Shown:** At k=64, 2 of 8 arms reach 150 of 300: `loop-s1-pre` (190 of 300) and `loop-s1-fresh` (166 of 300). This line and E50 are report-only, not validity or promotion gates.

| Paired seed | Practiced loop − fresh loop | Practiced loop − practiced plain | Fresh loop − fresh plain |
|---|---:|---:|---:|
| 0 | +30.33 pp (+728 of 2,400) | +17.21 pp (+413 of 2,400) | -1.79 pp (-43 of 2,400) |
| 1 | +29.79 pp (+715 of 2,400) | +17.71 pp (+425 of 2,400) | -3.50 pp (-84 of 2,400) |

**Shown:** Practiced loop exceeds its paired fresh loop and practiced plain on both seeds. The differences above are kept separate by seed. Fresh loop trails fresh plain on both seeds. **Suggested:** source practice helps this loop ruler, while the uneven k response and differing stop behavior merit caution about a general learning-curve claim. **Untested:** causality beyond these two paired seeds and these panels.

### Secondary holdout counts

These are recorded exact counts, in ascending positive-rung order. The 7×7 holdout has 48 items and the 11×11 holdout has 300; they are not treated as additional F_eq terms.

| Arm / seed | Size | 1 | 4 | 16 | 64 | 256 | 1,024 | 4,096 | 16,384 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| loop-s0-pre | 7×7 | 2 of 48 | 3 of 48 | 14 of 48 | 22 of 48 | 48 of 48 | 44 of 48 | 47 of 48 | 48 of 48 |
| loop-s0-pre | 11×11 | 0 of 300 | 0 of 300 | 5 of 300 | 71 of 300 | 157 of 300 | 190 of 300 | 124 of 300 | 200 of 300 |
| loop-s0-fresh | 7×7 | 0 of 48 | 4 of 48 | 13 of 48 | 19 of 48 | 30 of 48 | 18 of 48 | 17 of 48 | 27 of 48 |
| loop-s0-fresh | 11×11 | 0 of 300 | 7 of 300 | 17 of 300 | 25 of 300 | 75 of 300 | 27 of 300 | 41 of 300 | 47 of 300 |
| plain-s0-pre | 7×7 | 1 of 48 | 3 of 48 | 2 of 48 | 12 of 48 | 26 of 48 | 47 of 48 | 45 of 48 | 42 of 48 |
| plain-s0-pre | 11×11 | 0 of 300 | 1 of 300 | 0 of 300 | 5 of 300 | 29 of 300 | 54 of 300 | 65 of 300 | 68 of 300 |
| plain-s0-fresh | 7×7 | 0 of 48 | 0 of 48 | 4 of 48 | 5 of 48 | 34 of 48 | 28 of 48 | 36 of 48 | 35 of 48 |
| plain-s0-fresh | 11×11 | 0 of 300 | 0 of 300 | 0 of 300 | 6 of 300 | 39 of 300 | 46 of 300 | 17 of 300 | 54 of 300 |
| loop-s1-pre | 7×7 | 0 of 48 | 0 of 48 | 4 of 48 | 35 of 48 | 47 of 48 | 46 of 48 | 46 of 48 | 47 of 48 |
| loop-s1-pre | 11×11 | 0 of 300 | 0 of 300 | 1 of 300 | 109 of 300 | 182 of 300 | 176 of 300 | 193 of 300 | 144 of 300 |
| loop-s1-fresh | 7×7 | 0 of 48 | 1 of 48 | 9 of 48 | 31 of 48 | 36 of 48 | 0 of 48 | 36 of 48 | 22 of 48 |
| loop-s1-fresh | 11×11 | 0 of 300 | 0 of 300 | 23 of 300 | 85 of 300 | 72 of 300 | 0 of 300 | 63 of 300 | 1 of 300 |
| plain-s1-pre | 7×7 | 0 of 48 | 0 of 48 | 0 of 48 | 8 of 48 | 37 of 48 | 41 of 48 | 47 of 48 | 40 of 48 |
| plain-s1-pre | 11×11 | 0 of 300 | 0 of 300 | 0 of 300 | 5 of 300 | 37 of 300 | 103 of 300 | 79 of 300 | 92 of 300 |
| plain-s1-fresh | 7×7 | 0 of 48 | 0 of 48 | 2 of 48 | 12 of 48 | 34 of 48 | 26 of 48 | 41 of 48 | 37 of 48 |
| plain-s1-fresh | 11×11 | 0 of 300 | 0 of 300 | 1 of 300 | 10 of 300 | 43 of 300 | 49 of 300 | 47 of 300 | 30 of 300 |

## Old kinds and sleep

All values are dev old-kind correct counts written as “x of 200”. Each k branch is a separate copy. The **sleep gain 64** and **sleep gain 16,384** columns are after-sleep right count minus immediately pre-sleep right count (divide by two for percentage points). These gains are not the protocol's retention D.

| Arm / seed | Kind | Before maze | k64 before sleep | k64 after sleep | sleep gain 64 | k16384 before sleep | k16384 after sleep | sleep gain 16,384 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| loop-s0-pre | sums4 | 200 of 200 | 0 of 200 | 149 of 200 | +149 of 200 | 0 of 200 | 76 of 200 | +76 of 200 |
| loop-s0-pre | grids5 | 199 of 200 | 0 of 200 | 99 of 200 | +99 of 200 | 0 of 200 | 90 of 200 | +90 of 200 |
| loop-s0-fresh | sums4 | 0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 |
| loop-s0-fresh | grids5 | 0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 |
| plain-s0-pre | sums4 | 200 of 200 | 0 of 200 | 198 of 200 | +198 of 200 | 0 of 200 | 190 of 200 | +190 of 200 |
| plain-s0-pre | grids5 | 193 of 200 | 0 of 200 | 133 of 200 | +133 of 200 | 0 of 200 | 104 of 200 | +104 of 200 |
| plain-s0-fresh | sums4 | 0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 | 0 of 200 | 1 of 200 | +1 of 200 |
| plain-s0-fresh | grids5 | 0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 |
| loop-s1-pre | sums4 | 200 of 200 | 0 of 200 | 155 of 200 | +155 of 200 | 0 of 200 | 83 of 200 | +83 of 200 |
| loop-s1-pre | grids5 | 200 of 200 | 0 of 200 | 86 of 200 | +86 of 200 | 0 of 200 | 100 of 200 | +100 of 200 |
| loop-s1-fresh | sums4 | 0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 |
| loop-s1-fresh | grids5 | 0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 |
| plain-s1-pre | sums4 | 200 of 200 | 0 of 200 | 196 of 200 | +196 of 200 | 0 of 200 | 167 of 200 | +167 of 200 |
| plain-s1-pre | grids5 | 190 of 200 | 0 of 200 | 110 of 200 | +110 of 200 | 0 of 200 | 98 of 200 | +98 of 200 |
| plain-s1-fresh | sums4 | 0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 |
| plain-s1-fresh | grids5 | 0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 | 0 of 200 | 0 of 200 | +0 of 200 |

**Shown:** For the four practiced arms, old-kind accuracy is 0 of 200 on both kinds immediately after k=64 and k=16,384 (16 of 16 arm–kind–rung entries); sleep restores a positive count in all 16 of 16. Fresh arms start at 0 of 200 on these dev old-kind panels and stay essentially there. The source-qualification old panels and the adaptation `before` panels are distinct recorded evaluations, so their counts need not be identical.

Holdout 9×9 maze counts around sleep (after-sleep minus pre-sleep in parentheses):

| Arm / seed | k64 → sleep64 | k16384 → sleep16384 |
|---|---:|---:|
| loop-s0-pre | 137 of 300 → 156 of 300 (+19 of 300) | 274 of 300 → 289 of 300 (+15 of 300) |
| loop-s0-fresh | 49 of 300 → 67 of 300 (+18 of 300) | 104 of 300 → 85 of 300 (-19 of 300) |
| plain-s0-pre | 29 of 300 → 23 of 300 (-6 of 300) | 203 of 300 → 184 of 300 (-19 of 300) |
| plain-s0-fresh | 24 of 300 → 20 of 300 (-4 of 300) | 142 of 300 → 117 of 300 (-25 of 300) |
| loop-s1-pre | 190 of 300 → 146 of 300 (-44 of 300) | 255 of 300 → 283 of 300 (+28 of 300) |
| loop-s1-fresh | 166 of 300 → 142 of 300 (-24 of 300) | 18 of 300 → 173 of 300 (+155 of 300) |
| plain-s1-pre | 12 of 300 → 7 of 300 (-5 of 300) | 224 of 300 → 238 of 300 (+14 of 300) |
| plain-s1-fresh | 25 of 300 → 16 of 300 (-9 of 300) | 152 of 300 → 191 of 300 (+39 of 300) |

## Stopping and fixed-depth control

Holdout 9×9 positive-rung entries below give learned and fixed-depth correct counts, mean learned rounds, and cap hits; each count is written as “x of 300”. `L` is learned stopping and `F` is fixed depth. Fixed depth is 16 for loop and 1 for plain. A cap hit records reaching the 48-round limit; it is evidence about the stop behavior, not a wrong-answer count.

| Loop arm / seed | 1 | 4 | 16 | 64 | 256 | 1,024 | 4,096 | 16,384 |
|---|---|---|---|---|---|---|---|---|
| loop-s0-pre | L 1 of 300; F 1 of 300; 48.0 rounds; cap 300 of 300 | L 0 of 300; F 0 of 300; 48.0 rounds; cap 300 of 300 | L 28 of 300; F 28 of 300; 48.0 rounds; cap 300 of 300 | L 137 of 300; F 136 of 300; 48.0 rounds; cap 300 of 300 | L 256 of 300; F 245 of 300; 48.0 rounds; cap 300 of 300 | L 271 of 300; F 265 of 300; 48.0 rounds; cap 300 of 300 | L 257 of 300; F 243 of 300; 48.0 rounds; cap 300 of 300 | L 274 of 300; F 270 of 300; 31.9 rounds; cap 163 of 300 |
| loop-s0-fresh | L 0 of 300; F 0 of 300; 48.0 rounds; cap 300 of 300 | L 13 of 300; F 13 of 300; 21.1 rounds; cap 63 of 300 | L 34 of 300; F 35 of 300; 32.2 rounds; cap 168 of 300 | L 49 of 300; F 44 of 300; 47.9 rounds; cap 299 of 300 | L 144 of 300; F 144 of 300; 39.4 rounds; cap 223 of 300 | L 67 of 300; F 71 of 300; 48.0 rounds; cap 300 of 300 | L 85 of 300; F 72 of 300; 9.8 rounds; cap 8 of 300 | L 104 of 300; F 99 of 300; 48.0 rounds; cap 300 of 300 |
| loop-s1-pre | L 1 of 300; F 1 of 300; 48.0 rounds; cap 300 of 300 | L 0 of 300; F 0 of 300; 48.0 rounds; cap 300 of 300 | L 3 of 300; F 3 of 300; 13.4 rounds; cap 23 of 300 | L 190 of 300; F 185 of 300; 43.3 rounds; cap 262 of 300 | L 262 of 300; F 257 of 300; 48.0 rounds; cap 300 of 300 | L 236 of 300; F 227 of 300; 20.6 rounds; cap 71 of 300 | L 284 of 300; F 283 of 300; 34.8 rounds; cap 196 of 300 | L 255 of 300; F 253 of 300; 33.1 rounds; cap 177 of 300 |
| loop-s1-fresh | L 0 of 300; F 0 of 300; 48.0 rounds; cap 300 of 300 | L 1 of 300; F 1 of 300; 43.8 rounds; cap 262 of 300 | L 36 of 300; F 34 of 300; 43.3 rounds; cap 252 of 300 | L 166 of 300; F 168 of 300; 13.0 rounds; cap 5 of 300 | L 167 of 300; F 165 of 300; 11.9 rounds; cap 1 of 300 | L 0 of 300; F 0 of 300; 3.0 rounds; cap 0 of 300 | L 128 of 300; F 121 of 300; 15.6 rounds; cap 17 of 300 | L 18 of 300; F 19 of 300; 13.3 rounds; cap 0 of 300 |

| Loop arm / seed | Cap hits across eight rungs | Rungs capped on every item | Sum learned − fixed exact counts |
|---|---:|---|---:|
| loop-s0-pre | 2263 of 2,400 | 1, 4, 16, 64, 256, 1024, 4096 (7 of 8) | +36 of 2,400 |
| loop-s0-fresh | 1661 of 2,400 | 1, 1024, 16384 (3 of 8) | +18 of 2,400 |
| loop-s1-pre | 1629 of 2,400 | 1, 4, 256 (3 of 8) | +22 of 2,400 |
| loop-s1-fresh | 837 of 2,400 | 1 (1 of 8) | +8 of 2,400 |

**Shown:** For all four plain arm-seed pairs, every positive holdout rung has learned=fixed count, mean rounds 1.0, and 0 of 300 cap hits. On loop, some rungs saturate at 300 of 300 cap hits. A separate collapse appears for `loop-s1-fresh` at k=1,024: learned 0 of 300, fixed 0 of 300, mean 3.0 rounds, 0 of 300 cap hits; the fixed control also fails there. Thus the aggregate learned-versus-fixed differences are small relative to the practiced-loop advantage, but cap saturation and early stopping both appear in the recorded behavior. **Untested:** a formal stop-failure pass/fail verdict, because the permitted marks mention a “stop-failure rule” without defining its threshold or algorithm; and a causal claim that stopping alone caused any low score.

## Layout, update, and provenance checks

- **Shown from recorded metadata:** 8 of 8 adaptations list 16,384 support layouts, 0 reported support/panel overlaps, batch size 32, 512 batches and four updates per batch at each positive rung, hence 2,048 updates per rung. Each lists 512 updates for each of the two separate sleep branches. The visit counts at k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384 are 16,384, 4,096, 1,024, 256, 64, 16, 4, 1 respectively; `k × visits = 16,384` for 8 of 8 arms at all 8 of 8 rungs.
- **Shown from recorded metadata:** within each seed, 4 of 4 adaptation files and 4 of 4 holdout files share the same support SHA-256; the two seed hashes differ. Seed 0: `3efe54c5218d83ebc7b26e11899f9a2cd4dbbeb013521ccc69ef58dc84cabe2d`. Seed 1: `ad4a726c50a6e26a72339ecc046cc978d03068877e38e50042a93899b462677e`. All 8 of 8 files report dev panel sizes 7×7 = 24, 9×9 = 300, 11×11 = 300; holdout sizes 7×7 = 48, 9×9 = 300, 11×11 = 300. Every stored score count and cap count lies in 0…n and matches its reported panel n.
- **Shown from recorded metadata:** the loop has 1,645,726 weights and persistent coefficients, fixed depth 16, and learning rate 0.001; plain has 1,619,965, fixed depth 1, and learning rate 0.0005 in both seeds. These match the four source JSON summaries. Source training is recorded as 12,000 steps with batch 64 per source model. Adaptation `training_seconds` ranges 10,123–10,149 for loop and 7,186–7,194 for plain. The recorded 128+128 old-example replay allowance appears in the marks, but no allowed JSON field independently counts those replay items.
- **Untested from allowed inputs:** actual layout uniqueness, nested prefix/order, shuffle sharing, panel disjointness, optimizer-step execution, fp32 CPU mode, checkpoint reuse, and whether holdout was unopened until the gate. The JSON contains summaries and support hashes, not the layouts, optimizer trace, weights, predictions, or timestamps needed to verify those process claims. The `source` strings in the adaptation JSON name `/Users/ben-hannan/Desktop/projects/beautiful-model/...`, whereas this recount was requested in `/Users/ben-hannan/Downloads/beautiful-model/...`; this is a provenance-path mismatch, not a numerical discrepancy. No checkpoint file was inspected.

## Discrepancies, missing data, and interpretation

**Shown:** No arithmetic discrepancy was found between the dev gate and the permitted raw dev JSON, nor among recorded panel sizes, score bounds, support hashes, updates, visits, weight counts, and holdout summaries. The recorded 7×7 panel sizes are 24 dev and 48 holdout, so 7×7 counts must use those denominators. The four source checks, eight dev adaptations, and eight holdout summaries are present.

**Suggested:** Equal practice makes the practiced-loop advantage descriptive on this ruler, while total forgetting before sleep and loop cap saturation limit any interpretation as reliable skill retention or reliable learned stopping. The k=64 sleep changes holdout maze accuracy in both directions across arms; it cannot be treated as a guaranteed gain.

**Untested / unavailable:** The race addendum substitutes F_eq for F_all and cites design thresholds, but no design-arm raw JSON is among the permitted files, so no design-race result is scored here. The referenced race marks, old results, code, logs, and individual predictions were intentionally not read. The protocol's retention D and the stop-failure rule are not fully specified by the permitted marks; this report supplies explicitly named sleep gains and observable stop statistics instead of inventing a gate.
