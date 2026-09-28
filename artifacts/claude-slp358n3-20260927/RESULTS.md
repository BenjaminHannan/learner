# slp-358n3 official results (sleep gate H-B, the reasoner's nights)

Written 2026-09-28T18:53Z by helper S from the raw seed JSONs and the sealed PASSMARKS.md (sha256 c09a6163..., matches SEAL-code).
Scoring script: `scripts/claude_slp358n3_report_score.py`. Full numbers: `claude_slp358n3_report_score.json` (this folder).
Hash check of the copied records: `run-vast/HASHCHECK.txt` (script `scripts/claude_slp358n3_report_hashcheck.py`).
This is the small "night of sleep" test on the full-size loop reasoner (4 checkpoints, seeds 13-16, 2 x d512). It is not the
small card experiments and not the village model. The Thread manager's earlier unofficial count is not used here.
Every claim below is labelled shown (read off the records by code), suggested (a reading of the numbers) or untested.

## Verdict: PASS (H-B) — all five marks pass as written

| mark | result | detail |
|---|---|---|
| M1 learns from the day (S − R, after night 3) | **PASS** | day_sums: S − R = +110, +180, +129, +76 (seeds 13, 14, 15, 16), mean +123.8. day_grids: +85, +46, +74, +131, mean +84.0. Every difference is at least +20 on 4 of 4 seeds, both kinds. No seed hit the ceiling rule (both arms at 360 or more) or the floor rule (both at 40 or less): 4 of 4 seeds informative for both kinds, so my reading of "mean" and "3 of 4" did not matter. |
| M2 not a placebo (S − Z) | **PASS** | day_sums +381, +388, +379, +376; day_grids +366, +361, +353, +353. 4 of 4 seeds, both kinds, none uninformative. See caveat 2. |
| M3 no harm (S ≥ N − 6, after night 3) | **PASS** | harm_sums4: S = N = 300 of 300 on 4 of 4 seeds. harm_grids5: S = N = 300 of 300 on 4 of 4 seeds. S − N = 0 in all 8 cases. See caveat 1. |
| M3b retention (S lost ≤ 15 of 300, every night) | **PASS** | S lost 0 of 300 on all 4 seeds, all 3 nights, both tests (24 of 24 cells are 0). |
| RESUME | **PASS** | `resume.json`: weights identical true, optimizer identical true, the 150 batches after the resume identical to the straight run true, return codes [0, 3, 0] (the middle run stopped on purpose), stop step 150, 300 night steps, batch 256, RESUME_identical true. |

"Proved wrong" test (S − R ≤ +5 on both kinds on 3 of 4 seeds): 0 of 4 seeds meet it. Not proved wrong. (shown)

Predictions made before the run: M1 55%, M3/M3b 75%, RESUME 90%, PASS 40%. PASS happened; M1 passed by far more than the mark.

## What the numbers say (right answers out of N, mean of 4 seeds, after night 3)

| arm | day_sums (of 400, size 12) | day_grids (of 400, size 7) | harm_sums4 (of 300) | harm_grids5 (of 300) |
|---|---|---|---|---|
| N no night | 257.2 | 260.0 | 300 | 300 |
| R rehearsal only | 257.2 | 274.2 | 300 | 300 |
| S sleep | **381.0** | **358.2** | 300 | 300 |
| Z placebo | 0.0 | 0.0 | 287.5 | 299.2 |

- shown: S beats R by a wide margin on both day kinds on every seed; R is about the same as N (day_sums +0.0 on average, day_grids +14.2, with seed 14 day_sums at 208 against N 228).
- shown: the report-only puzzle sizes moved the same way. S vs N, means of 4 seeds: sums6 199.8 vs 199.0, sums8 198.2 vs 183.8, sums10 194.8 vs 161.0, grids6 196.5 vs 191.8. R: 198.8, 185.0, 159.2, 191.2.
- shown: the reasoner also stops earlier after S (mean stop round, day_sums 9.94 vs N 10.95; day_grids 17.02 vs N 25.38). Fixed-8 and fixed-48 scores (mean of 4 seeds): day_sums S 379.5 / 384.0, N 255.0 / 258.8; day_grids S 323.8 / 358.8, N 250.5 / 260.0. The gain is not only a stop-rule effect (fixed-48 shows it too).
- shown: day tries (the 300 fresh puzzles each arm attempts before its night): all five arms are identical on day 1 (same net, as they should be). On days 2 and 3, S beats N on every seed and kind (for example seed 13 day 3 sums 277 vs 190, grids 269 vs 214). Full table in the JSON.
- shown: excluded day items: 0 on all 4 seeds.

## L arm (longer nights, 6,000 steps; seeds 13 and 14 only; report only, decides nothing)

| after night 3, mean of seeds 13-14 | day_sums | day_grids | harm_sums4 | harm_grids5 | sums10 | grids6 |
|---|---|---|---|---|---|---|
| N | 245.5 | 286.0 | 300 | 300 | 159.0 | 193.0 |
| S | 384.5 | 363.5 | 300 | 300 | 195.5 | 197.0 |
| L | 389.5 | 278.5 | 300 | 300 | 197.0 | 193.0 |

- shown: L is about the same as S on sums (389.5 vs 384.5) and clearly lower than S on day_grids (278.5 vs 363.5; L is at about the N level, 286.0: seed 13 night 3 L 290 vs N 293, seed 14 L 267 vs N 279). L − S on day_grids: seed 13 −76, seed 14 −94.
- shown: L lost counts: 1 (harm_grids5, seed 13, night 1), otherwise 0, so 1 of 12 cells is not zero and the largest is 1 of 300.
- suggested: a night 20 times longer did not teach the grid kind more than the short night did. Possible reasons (untested): the long night's day/rehearsal mix drifts, or the 6,000-step night is at a learning rate that is too high for grids. The L arm is not judged by the pass marks, so nothing here changes the verdict.
- untested: whether L on seeds 15 and 16 would look the same (L was not run there, by design).

## Caveats (please read before quoting the PASS)

1. **The harm tests are at the ceiling.** N scores 300 of 300 on harm_sums4 and harm_grids5 on all 4 seeds, so "S ≥ N − 6" and "lost ≤ 15" can only be failed by a large loss. They were passed with 0. The sealed rules have no ceiling clause for M3, so M3 is scored as written, but (suggested) it is weak evidence that a night does no small harm; report-only sizes above (sums6 to grids6) show no loss either.
2. **The placebo night broke the net.** Z scores 0 of 400 on both day kinds on all 4 seeds (and lost up to 229 of 300 harm_sums4 items after night 1 on seed 15). So M2 passes with the widest possible gap, but (suggested) it mostly shows that wrong answers hurt, not that right answers help more than any small update. The fair comparison for "learns from the day" is R, and that is M1.
3. **Day sizes.** sums 12 and grids 7 were chosen by the fixed rule (sums 10 had a 4-seed mean of 242.0, just over 240; sums 12 had 200.75; grids 6 had 285.25, grids 7 had 212.0). Same for every seed and arm. Recomputed from sizes.json: same sizes. (shown)
4. **Seed 16 is different from the others at the start** (base day_grids 184 against 279 to 293 on seeds 13-15), and seed 16 R gained +38 on day_grids over N. S − R there is still +131. (shown)
5. **RESUME details** (CPU, float32, deterministic algorithms, 4 threads) are read from the sealed code (`nights_only`), not from the record, which does not store them. The saved .pt states are not in git, so I did not re-run torch.equal; I read the sealed check's own result. (untested by me)
6. **This is the code-answers night.** PASSMARKS.md says a PASS licenses this night in 0.2d with code answers as disclosed scaffolding; it does not license a night built from the reasoner's own checked tries (a later test), and it is about code-made sums and Latin grids, not chat puzzles.

## Record integrity (details in run-vast/HASHCHECK.txt)

- SEAL-code.sha256.txt against the code and test files on main: **18 of 18 match**, including PASSMARKS.md.
- run-vast/MANIFEST.sha256 (30 lines): **22 of 30 match**, including all 4 seed JSONs, all logs, sizes.json, resume.json, SEAL-run. **7 lines are checkpoints/resume states** (S-final.pt x4, resume.pt, stop-state.pt, straight.pt): weights are never in git, so they cannot be re-hashed here. **1 line differs**: `W/pip.log` against the copied `run-vast/pip-tail.txt`. The copy is named "tail", so it is most likely a different file from the manifest's full pip.log (suggested); the pip log has no bearing on any score.
- SEAL-run.sha256.txt: 4 of 4 S-final.pt hashes agree with the MANIFEST hashes for the same files. (The .pt files themselves are not on main.)
- Records were copied byte-for-byte from origin/builder-outbox (nothing of those paths existed on main before). Collected 2026-09-28T09:04:10Z; the guard logged spend 0.48 (dollars) for the run. torch 2.11.0+cu128, NVIDIA GeForce RTX 3090; minutes 53.5, 53.3, 14.6, 14.7 (seeds 13-16; 13 and 14 include the L arm).

## Plain-language summary for Ben

The sleep test passed. When the reasoner "sleeps" on the day's puzzles with the right answers (arm S), it gets about 120 more sums and 85 more grids right out of 400 than when it sleeps the same length on old practice only (arm R). That was true on all 4 of 4 seeds, and the mark only needed 20. Its old skills were not hurt (0 of 300 lost, every night, every seed), and the stop-and-resume check gave exactly identical weights. Two honest warnings: the old-skill tests were already at 300 of 300, so they can only catch big damage, and the "placebo" night just wrecked the net, so that comparison is easy to pass. The longer night (L, two seeds, report only) helped sums about as much as S but did not help grids, so longer is not better here.
