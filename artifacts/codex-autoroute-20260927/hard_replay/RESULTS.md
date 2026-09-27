# Targeted grid5 replay result

**Verdict: FAIL (not proved wrong).**

## Shown

Each score is exact items correct out of 200 at the model's own stopping rule. T is grids5 + sums4 + maze7 after C, out of 600. All threshold decisions used integer sums.

| Seed | A grids base / targeted | B sums base / targeted | C grids base / targeted | C sums base / targeted | C maze base / targeted | T base / targeted | ΔT | Minutes base / targeted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 61 | 192 / 194 | 200 / 200 | 116 / 117 | 199 / 193 | 152 / 147 | 467 / 457 | -10 | 11.51 / 11.64 |
| 62 | 198 / 198 | 200 / 200 | 137 / 167 | 197 / 193 | 136 / 134 | 470 / 494 | +24 | 11.24 / 11.23 |
| 63 | 197 / 197 | 200 / 200 | 160 / 154 | 191 / 198 | 145 / 131 | 496 / 483 | -13 | 11.11 / 11.58 |
| 64 | 197 / 197 | 200 / 200 | 146 / 162 | 184 / 188 | 121 / 150 | 451 / 500 | +49 | 11.49 / 11.51 |
| 65 | 198 / 198 | 200 / 200 | 138 / 162 | 198 / 198 | 144 / 119 | 480 / 479 | -1 | 11.03 / 11.28 |
| 66 | 200 / 199 | 200 / 200 | 165 / 173 | 194 / 184 | 130 / 136 | 489 / 493 | +4 | 11.16 / 11.19 |

Mean C grids: **143.67 baseline / 155.83 targeted**; mean B sums: **200.00 / 200.00**; mean C mazes: **138.00 / 136.17**; mean C T: **475.50 / 484.33**. Targeted replay won T on **3/6** seeds.
Mean recorded minutes: **11.26 baseline / 11.41 targeted**.

| Registered check | Pass | Exact integer comparison |
| --- | --- | --- |
| M1 mean grid C ≥180 | False | 935 ≥ 1080 |
| M1 every grid C ≥160 | False | Per-seed rows above |
| M2 mean sums B ≥195 | True | 1200 ≥ 1170 |
| M2 maze within 10 | True | 817 ≥ 828 − 60 |
| M3 T +40 | False | 2906 ≥ 2853 + 240 |
| M3 T wins ≥5/6 | False | 3 ≥ 5 |
| M4 integrity, MPS, precision, sizes, budgets and full recount | True | All 12 results and the independent full recount validated |

Phase counts checked in every file: A 2500 grids; B 250 grids/2250 sums; C 75 grids/75 sums/1350 mazes in both arms. All eight kind-and-size counters were present in each phase and summed to the corresponding kind count. Targeted B/C old-grid replay used only grid5 (250/75 batches). Each arm used 6500 steps and 400 replay batches per seed, with batch 64 and 1,646,750 parameters on float32 MPS. All 12 runs report software commit `b5a1dd133327c9c335781f25ac7859e06a50ba31` and passing initial/final M4 controls. Independent full recount: `/Users/ben-hannan/.codex/worktrees/retention-isolation/beautiful-model/artifacts/codex-autoroute-20260927/hard_replay/RECOUNT-FINAL.json`; all 36 phase scores match and all 12 final checkpoints replayed 600 requests with zero prediction, stop or context mismatches.

| Seed | B grid4/grid5 baseline | B grid4/grid5 targeted | C grid4/grid5 baseline | C grid4/grid5 targeted |
| --- | ---: | ---: | ---: | ---: |
| 61 | 117/133 | 0/250 | 39/36 | 0/75 |
| 62 | 124/126 | 0/250 | 44/31 | 0/75 |
| 63 | 133/117 | 0/250 | 32/43 | 0/75 |
| 64 | 121/129 | 0/250 | 34/41 | 0/75 |
| 65 | 127/123 | 0/250 | 40/35 | 0/75 |
| 66 | 130/120 | 0/250 | 40/35 | 0/75 |

Report-only learned-context agreement (diagnostic-majority map applied to final inputs; correct kind / 600): s61 301 / 350, s62 329 / 318, s63 473 / 452, s64 398 / 396, s65 410 / 434, s66 436 / 431.

## Suggested

A score difference may suggest that concentrating the fixed old-grid replay slots on grid5 changes its retention. The registered checks include sums and maze learning; they do not establish a generally optimal practice selection policy.

## Untested

Grid4 retention, other replay selections, other tasks, larger models, language-model behavior, and ambiguous or reformatted requests are outside this grade. Both arms use learned context and mixed single-request inference, but its causal benefit versus oracle or other routing is not isolated. Equal optimizer and replay-batch counts do not imply equal compute because grid5 batches can take longer.

## Plain words

Both models had the same number of practice batches. In the later stages, one practised only five-cell grids in its old-grid batches, while the other practised four- and five-cell grids. The table shows whether that helped it remember the tested five-cell grids while still learning sums and mazes. The verdict follows the rules fixed before training.

## Completion notes: checked retention through all stages

These are report-only details from the independently recounted scores. They do not change any mark. Grid5 means the logical 5×5 grid task (not a five-cell puzzle).

| Seed | Grids after A, baseline / targeted | Grids after B, baseline / targeted | Grids after C, baseline / targeted |
| --- | ---: | ---: | ---: |
| 61 | 192 / 194 | 167 / 176 | 116 / 117 |
| 62 | 198 / 198 | 184 / 197 | 137 / 167 |
| 63 | 197 / 197 | 174 / 193 | 160 / 154 |
| 64 | 197 / 197 | 180 / 189 | 146 / 162 |
| 65 | 198 / 198 | 171 / 185 | 138 / 162 |
| 66 | 200 / 199 | 192 / 199 | 165 / 173 |
| Mean | 197.00 / 197.17 | 178.00 / 189.83 | 143.67 / 155.83 |

**Shown:** targeted replay reduced the mean final grid loss from 53.33 to 41.33 items relative to each arm's own A score. It still lost roughly 41 of 200 previously learned grids. Two candidate seeds finished below the required floor of 160 (117 and 154); no candidate reached 180. The final grid gain was 12.17 and T gain was 8.83, with T wins on 3/6 seeds. M1 and M3 failed; M2 and M4 passed. Neither registered falsifier fired, so the exact verdict remains **FAIL (not proved wrong)**.

**Suggested:** concentrating practice on the evaluated grid size gives a modest, inconsistent improvement in this setting. It is insufficient protection against later maze training. This comparison does not establish the underlying cause of forgetting or rule out learned control of updates.

## Time, exposure and preparation record

All twelve trajectories took **135.98 recorded minutes** including their evaluation and controls; the separate full recount took **6.09 minutes**, for **142.07 minutes** combined. Preparation, publication and idle monitoring are excluded. Driver start was 2026-09-27 14:59:06 UTC; the final baseline ended at 17:15:21 UTC. Driver session 36630 and recount session 6506 each returned exit code 0. Recount ran 17:19:07–17:25:13 UTC, PID 56335 on MacBook-Pro.

Mean training-only time was 9.48 minutes baseline versus 9.62 targeted; phase scoring added 1.46 versus 1.47 minutes. Total mean trajectory time was 11.26 versus 11.41 minutes (about 1.3% longer for targeted replay). These timings do not prove equal hardware work. Each trajectory used 416,000 training examples, including 25,600 old replay examples. Full kind/size counters and timing calculations are preserved in [SUPPLEMENTARY-STATS.json](SUPPLEMENTARY-STATS.json).

The initial preflight failed a test-only assertion about the grid tensor shape before model construction, with no optimizer updates. Its OS PID was not captured. The corrected preflight passed with PID 67716, also with zero optimizer updates. This preparation provenance gap is preserved in [RUN-NOTE.md](RUN-NOTE.md) and [IMPLEMENTATION-NOTE.md](IMPLEMENTATION-NOTE.md). Training and final recount used the unchanged published scientific software.

## Panels, repeatability and scope limits

The six final panels and six diagnostic panels contain 5,400 requests in total, but only **4,478 distinct visible inputs**: 1,800 grids, 1,800 sums and 878 mazes. There are 572 fingerprints repeated across seeds. Each seed's final and diagnostic panels are individually unique and mutually disjoint. Cross-seed maze repetition limits panel independence; six seeds do not imply 1,200 distinct final maze questions. Exact practice matches to the same seed's final or diagnostic panel were rejected. The resulting maze-practice distribution is filtered and should not be treated as identical to an unfiltered generator.

| Seed | Rejected sums, baseline / targeted | Rejected mazes, baseline / targeted |
| --- | ---: | ---: |
| 61 | 7 / 8 | 19154 / 19273 |
| 62 | 5 / 3 | 18916 / 17889 |
| 63 | 2 / 8 | 18833 / 19129 |
| 64 | 3 / 8 | 19683 / 18515 |
| 65 | 8 / 1 | 18213 / 18033 |
| 66 | 6 / 8 | 18489 / 18453 |

Grid practice rejections were zero in all runs. The candidate consumes the ordinary grid-size draw before overriding it; choosing different sizes changes later generator consumption. The arms therefore share registered seeds and distributions, not identical post-A examples.

Common phase-A training is not bitwise reproducible on this MPS setup: seed 61 finished at 192 versus 194 and seed 66 at 200 versus 199 despite the same A recipe. The cause is not isolated. Exact inference reproducibility is separately shown by all 7,200 checkpoint requests matching predictions and stop/context probabilities. No extra noise calibration or statistical-significance claim is made.

All primary scores came from shuffled mixed requests using only tokens and answer-slot masks. Learned context receives no kind-label target. Its report-only agreement above is a diagnostic of one argmax summary, not evidence that four contexts correspond to four distinct skills. No kind map enters inference.

**Untested:** grid4 retention; a learned sleep-time controller; MoE as a new candidate here; permanent or lifelong retention; natural-language requests; the reader/talker, 1B chat model and joined build. AR1 is a separate registered experiment and is not pooled with AR2.

## Review and reproduction

The independent [recount.py](recount.py) checks saved answers at the registered own-stop rule, every panel/source hash, all phase budgets and final checkpoint replay. [grade_results.py](grade_results.py) applies the immutable marks and exact verdict precedence. The checked archived outputs are [RECOUNT-FINAL.json](RECOUNT-FINAL.json) and [RESULTS.json](RESULTS.json).

From the repository root, a reviewer can run the following with the existing project Python; the output names must be new. The grader consumes the archived RECOUNT-FINAL.json, so compare the new independent recount with that archived report as well.

```sh
/Users/ben-hannan/premonition-chat/chatdemo-venv/bin/python -B artifacts/codex-autoroute-20260927/hard_replay/recount.py --out artifacts/codex-autoroute-20260927/hard_replay/RECOUNT-REVIEW.json
/Users/ben-hannan/premonition-chat/chatdemo-venv/bin/python -B artifacts/codex-autoroute-20260927/hard_replay/grade_results.py --out artifacts/codex-autoroute-20260927/hard_replay/RESULTS-REVIEW.md
```

## For Ben

We used one small network that chooses what to do from the puzzle itself. During later learning, we directed its existing grid practice toward the harder 5×5 grids. It remembered about 156 of 200 grids instead of 144, while learning sums fully and mazes about as well. That is some improvement, but it had originally learned about 197 grids: it still forgot too much. This recipe failed the agreed test. It does not yet behave like your example of remembering how to ride a bike.
