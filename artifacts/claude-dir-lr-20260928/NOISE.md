# Noise of F_eq and F_few, from the raw eq-runs files

Written 2026-09-28 21:49 UTC. Script: `scripts/claude_dir_lr_noise.py`, output `artifacts/claude-dir-lr-20260928/noise-from-raw.txt` (dev = `adapt.json`, holdout = `holdout.json`, 9x9, learned-stop `right` of 300).

**Shown (from the files):**
- The research note's "about 10 F_eq" is not in the baseline files. Its source (H9 finding 4) is the sparse-loop design's effect being +3.88 in seed 0 and -6.25 in seed 1, which is a difference between two treatment effects, not baseline noise.
- H12's 3.33 (F_eq) and 4.17 (F_few) are reproduced exactly from the **practised loop's dev curves alone**: rung gaps seed 0 minus seed 1, root-mean-square divided by the square root of the number of rungs (8 or 4).
- The same recipe over **all four starts** (practised/fresh loop, practised/fresh plain) gives **3.96** (F_eq) and **5.23** (F_few) on dev; 4.03 F_eq on holdout.
- Direct same-start seed gaps in F_eq (dev): -0.46, -1.33, +1.42, -2.12 (RMS 1.46, largest 2.12); holdout: -0.29, -0.83, +0.21, -2.54 (largest 2.54). Direct F_few seed gaps (dev): loop-pre -2.33, loop-fresh -8.75, plain-pre +1.67, plain-fresh -0.25.

**Suggested:** each seed also has its own source net, so seed gaps mix training noise with source-net differences; the rung recipe treats rungs as independent, which the direct gaps say is too pessimistic for F_eq. Four gaps per column is too few to trust a spread. **Untested:** same-start, same-seed rerun noise (Lead 0's 1e-3 control rerun measures whether the ruler is even bit-reproducible on the run machine).

**What I commit to for marks:** the larger, all-starts number, doubled: **F_eq bar +8.0** (2 x 3.96 = 7.93), **F_few bar +10.5** (2 x 5.23 = 10.47). These sit above H12's 7.0 / 8.5 and far above the direct gaps.
