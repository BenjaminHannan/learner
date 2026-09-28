# E: does practice shorten the learned thinking time? (existing files only, no training)
Written 2026-09-28 (date -u at commit). Source: artifacts/claude-fewex-20260927/eq-runs/loop-s{0,1}-{pre,fresh}/{holdout,adapt}.json. Script: scripts/claude_dir_e_thinktime_count.py, output counts.txt. No saved nets exist in the repo, so nothing was re-run. Scope: the loop reasoner on mazes and the two old kinds; not the small card experiments, not the village model.

## Answer (plain words)
**Not shown.** The one hint (seed 0, practised loop: 31.9 rounds at k=16384 and 10.0 after sleep16384, 9x9) is real in the files but it is one run. Across all 4 loop runs the pattern does not hold consistently.

## Counts (9x9 holdout; rounds are the mean learned thinking time, cap 48)
| run | rungs k=1..16384 below cap (<47 rounds) | mean rounds, low half k=1,4,16,64 | mean rounds, high half k=256..16384 | Spearman(k, rounds) 9x9 |
|---|---|---|---|---|
| practised loop seed 0 | 1 of 8 (only k=16384) | 48.0 | 44.0 | -0.58 |
| practised loop seed 1 | 5 of 8 | 38.2 | 34.1 | -0.46 |
| fresh loop seed 0 | 4 of 8 | 37.3 | 36.3 | +0.07 |
| fresh loop seed 1 | 7 of 8 | 37.0 | 10.9 | -0.64 |

- **Shown:** practised loop seed 0 sat at the 48 cap on 300 of 300 mazes at every rung k=1..4096 on 9x9 (11x11 also 300 of 300; 7x7 at least 47 of 48), then fell to 31.9 rounds (163 of 300 at cap) at k=16384 and 10.0 (8 of 300) after sleep16384, with right answers 274 and 289 of 300.
- **Shown, seed 1 does not repeat it cleanly:** practised loop seed 1 goes 13.4 (k=16), 43.3 (64), 48.0 (256), 20.6 (1024), 34.8 (4096), 33.1 (16384): 3 drops and 3 rises between neighbouring rungs. Sleep16384 gives 27.1 rounds, 134 of 300 at cap.
- **Shown, the untrained-on-practice control moves as much:** fresh loop seed 1 falls to 3.0 rounds with 0 of 300 right at k=1024, and fresh seed 1 sits between 3.0 and 15.6 rounds for k>=64. Short thinking there is not "faster because practised" (it is often wrong: 0 of 300 at k=1024, 18 of 300 at k=16384).
- **Shown, sleep:** sleep16384 vs k=16384 (9x9) mean rounds: practised s0 31.9 to 10.0 (down); practised s1 33.1 to 27.1 (down); fresh s0 48.0 to 48.0 (same); fresh s1 13.3 to 21.6 (UP). 2 of 4 down clearly, 1 same, 1 up.
- **Shown, other kinds (old sums4/grids5, right out of 200):** thinking got longer, not shorter, after maze practice. Practised seed 0: sums4 5.5 rounds (200 right) before, 39.9 after k=64, 11.7 after k=16384 (0 right); grids5 9.1 to 47.4 to 26.7. Seed 1: sums4 6.5 to 48.0 to 26.4; grids5 11.1 to 48.0 to 38.8. All 8 old-kind cells after maze practice (4 runs x 2 kinds, at k=64 and k=16384 each: 16 cells) have 0 of 200 right. So on the kinds practised in the source net, learned thinking was short and right, and maze practice broke both.
- **Shown:** across the 32 practised/fresh loop 9x9 cells, rank correlation of mean rounds with right count is -0.11: short thinking does not go with more right answers.

## Why the stop cannot be read as "learning" yet
**Shown (H9 REPORT section 2, and scripts/claude_fewex_bench.py:205 "no maze stop-head loss"):** the stop head is never trained on mazes in the ruler, so its maze behaviour is what an untrained head does after other weights change. Fresh loop seed 1 at k=1024 (3.0 rounds, 0 right) is the giveaway: the same head stops at round 3 on every maze. **Suggested:** the seed-0 drop is the untrained head crossing its threshold as weights drift, not the net learning that mazes are easy. **Untested:** whether a trained stop shows the human-like pattern.

## Verdict for the roadmap
Question not answerable from the existing files. The clean test needs the stop trained on mazes first (thread "Train the stop on mazes", H12). Sealed test proposed in PASSMARKS.md as a readout of H12's runs, no extra training.
