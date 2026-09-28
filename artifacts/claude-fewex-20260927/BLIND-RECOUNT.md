# Blind recount

Inputs: `PASSMARKS.md`, `RACE-PASSMARKS.md`, the four specified `source.json` files, six available `adapt.json` files, and two `partial.json` files only. This is arithmetic over the recorded JSON aggregates, not a rerun of models or an inspection of individual examples. I treat `rungs` in the full adaptation files as the requested **dev** ladder; those files do not label a separate holdout score series.

## Gate result

**Shown from the recorded counts: V1 passes, V2 passes, V3 fails. The sealed baseline result is INCONCLUSIVE.** On 300-example 9×9 dev rungs, “strictly above 10% and below 90%” means **31 through 269 correct**, excluding 30 and 270. No arm has the required three qualifying *positive* rungs. The highest observed count is two. For each partial arm, only the 65,536 rung is missing, so even a qualifying result there cannot produce three. The race marks do not activate.

| Source-trained arm | Sums /200 | Grids /200 | V1 | 2-D matrices with live-gradient check | Missing on both batches | V2 | Weights = persistent coefficients | Source train min |
|---|---:|---:|---|---:|---|---|---:|---:|
| loop s0 | 200 | 200 | pass | 16 | none | pass as recorded | 1,645,726 | 46.22 |
| loop s1 | 200 | 200 | pass | 16 | none | pass as recorded | 1,645,726 | 46.77 |
| plain s0 | 200 | 195 | pass | 51 | none | pass as recorded | 1,619,965 | 16.91 |
| plain s1 | 200 | 191 | pass | 51 | none | pass as recorded | 1,619,965 | 26.21 |

V1's floor is 190/200 for each kind. V2 uses the recorded `nonzero_all: true`, matrix counts, and empty `missing_both` lists. The permitted inputs contain no gradients or checkpoints with which to repeat the one-step check.

## 9×9 dev ladder

Each rung entry is correct out of 300. `F_all` is the sum across nine positive rungs divided by 2,700; `F_few` uses rungs 1, 4, 16, and 64 divided by 1,200. The zero rung is excluded. All percentages below are dev calculations, not holdout results.

| Arm | 1 | 4 | 16 | 64 | 256 | 1,024 | 4,096 | 16,384 | 65,536 | In-band rungs | Dev F_all | Dev F_few |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| loop s0 pre | 0 | 1 | 0 | 2 | 0 | 2 | 82 | 271 | 300 | 1: 4,096 | 658/2,700 = 24.3704% | 3/1,200 = 0.2500% |
| loop s0 fresh | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 17 | 283 | 0 | 303/2,700 = 11.2222% | 0% |
| plain s0 pre | 0 | 0 | 0 | 2 | 0 | 0 | 76 | 190 | 279 | 2: 4,096, 16,384 | 547/2,700 = 20.2593% | 2/1,200 = 0.1667% |
| plain s0 fresh | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 144 | 270 | 1: 16,384 | 416/2,700 = 15.4074% | 0% |
| plain s1 pre | 7 | 1 | 6 | 1 | 7 | 0 | 42 | 225 | 273 | 2: 4,096, 16,384 | 562/2,700 = 20.8148% | 15/1,200 = 1.2500% |
| plain s1 fresh | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 149 | 287 | 1: 16,384 | 437/2,700 = 16.1852% | 0% |
| loop s1 pre, partial | 0 | 0 | 0 | 1 | 0 | 5 | 46 | 282 | unavailable | 1 observed; at most 2 | unavailable; bound 12.3704–23.4815% | 1/1,200 = 0.0833% |
| loop s1 fresh, partial | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | unavailable | 0 observed; at most 1 | unavailable; bound 0–11.1111% | 0% |

At 16,384, loop s0 pre has 271/300 and loop s1 pre has 282/300, both above the strict upper cutoff. Plain s0 fresh has exactly 270/300, also excluded. The partial bounds allow the missing 65,536 count to be anywhere from 0 to 300. Every observed 64-example dev rung is below the report-only 50% line.

Paired **dev** pre-minus-fresh differences: loop s0 `F_all` +13.1481 points and `F_few` +0.2500; plain s0 +4.8519 and +0.1667; plain s1 +4.6296 and +1.2500. Loop s1 `F_all` is unavailable; its `F_few` pre-minus-fresh difference is +0.0833 points. Loop pre versus plain pre on the one complete paired seed (s0) is +4.1111 `F_all` points. No two-seed loop comparison can be calculated.

## Old kinds and sleep

All scores are correct out of 200, written **sums/grids**. I calculate forgetting `D` in percentage points for each kind as `(before-adaptation right − post-sleep right)/2`. Thus negative `D` means a gain. The `after 64` and `after 64k` columns are the pre-sleep stream measurements; the `sleep` columns are the separate branch endpoints.

| Full arm | Before | After 64 | After 64k | Sleep 64 | D64 pp | Sleep 64k | D64k pp |
|---|---|---|---|---|---|---|---|
| loop s0 pre | 200/199 | 92/11 | 0/0 | 194/176 | 3.0/11.5 | 3/0 | 98.5/99.5 |
| loop s0 fresh | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| plain s0 pre | 200/193 | 32/153 | 0/0 | 199/159 | 0.5/17.0 | 6/1 | 97.0/96.0 |
| plain s0 fresh | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| plain s1 pre | 200/190 | 195/155 | 0/0 | 188/145 | 6.0/22.5 | 11/0 | 94.5/95.0 |
| plain s1 fresh | 0/0 | 0/0 | 0/0 | 1/0 | −0.5/0 | 0/0 | 0/0 |

| Partial arm | Before | After 64 | Sleep 64 | D64 pp | Sleep-64 dev 9×9 |
|---|---|---|---|---|---|
| loop s1 pre | 200/200 | 143/128 | 187/178 | 6.5/11.0 | 9/300 |
| loop s1 fresh | 0/0 | 0/0 | 1/0 | −0.5/0 | 0/300 |

The partial files provide no after-64k old-kind score, 64k sleep endpoint, or D64k. Across the full pre arms, 64k sleep leaves sums/grids near zero; the 64-example sleep branch retains more old-kind accuracy. These are the recorded dev outcomes, not a valid baseline win claim after V3 fails.

## 65,536 rung and resources

The 65,536 entries below give **learned-stop correct / n (fixed-depth correct; mean rounds; cap hits)**. The selected source fixed depth is 16 for loop and 1 for plain. The loop has a 48-round cap; plain uses one round. The fixed-versus-learned gaps can be read directly from the first two counts.

| Full arm | 7×7 | 9×9 | 11×11 | Adapt train min |
|---|---|---|---|---:|
| loop s0 pre | 24/24 (24; 46.54; 23) | 300/300 (300; 48.00; 300) | 272/300 (262; 48.00; 300) | 77.43 |
| loop s0 fresh | 24/24 (24; 17.71; 3) | 283/300 (282; 20.62; 39) | 199/300 (188; 28.44; 79) | 77.40 |
| plain s0 pre | 24/24 (24; 1.00; 0) | 279/300 (279; 1.00; 0) | 130/300 (130; 1.00; 0) | 48.62 |
| plain s0 fresh | 24/24 (24; 1.00; 0) | 270/300 (270; 1.00; 0) | 127/300 (127; 1.00; 0) | 48.95 |
| plain s1 pre | 23/24 (23; 1.00; 0) | 273/300 (273; 1.00; 0) | 115/300 (115; 1.00; 0) | 49.23 |
| plain s1 fresh | 24/24 (24; 1.00; 0) | 287/300 (287; 1.00; 0) | 132/300 (132; 1.00; 0) | 49.26 |

Each full file reports 64 distinct support layouts, 65,536 distinct stream layouts, zero stream–support overlap, and zero stream–panel overlap. The panel-layout fields read **dev: 24/300/300** and **holdout: 48/300/300** for 7×7/9×9/11×11, identically in all six files. Those layout and overlap values are aggregate claims in the JSON; individual layouts are unavailable for independent duplicate checking. Each full adaptation reports 8,192 stream optimizer updates and 512 updates in each sleep branch. Loop weights and persistent coefficients are both 1,645,726; plain's are both 1,619,965, a difference of 25,761 (1.5653% of loop). The partial files omit adaptation time, adaptation weight/layout/overlap fields, optimizer updates, and all 65,536 scores. No permitted input gives raw example-memory bytes or allowance, so that item cannot be verified.

Arithmetic cross-check: all reported right, fixed-right, and cap-hit counts lie between zero and their denominators; full files contain zero plus all nine positive rungs; partial files contain zero plus exactly eight positive rungs; all 9×9 rung denominators are 300; all old-kind denominators are 200; and the displayed sums, percentages, and paired differences were recomputed from the rung counts. No holdout accuracy can be calculated from the permitted JSON despite its holdout layout counts.

## Plain-language readout for Ben

- **Shown:** All four source-trained models clear the two old-task accuracy floors. The JSON reports nonzero live gradients for every checked weight matrix. The dev ladder fails its predeclared usability gate in every arm, even granting either partial arm the best possible missing rung. Per the marks, the baseline is **INCONCLUSIVE** and the design race is not scored.
- **Suggested:** On seed 0, the pretrained loop's dev 9×9 mean exceeds its fresh copy by 13.15 points and pretrained plain by 4.11 points; at the four few-example rungs, all full arms remain at or below 1.25%. Large late-rung gains coexist with substantial long-branch forgetting of sums and grids.
- **Untested with these inputs:** A two-seed loop advantage, holdout `F_all`, raw-memory allowance, independent replay of the gradient check, and any Test A/B/C promotion or rejection. The missing loop s1 65,536 result and 64k branch cannot be inferred from the partial files.
