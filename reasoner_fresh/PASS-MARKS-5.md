# Marks for varied training wording (arm M), fixed before training (2026-10-03, fast lane; same sealed eval form)

Change (one): the training stream is half the old 4 templates and half 180 procedurally composed frames (gen2.py), instead of the old 4
templates only. Everything else as the copy-path arm (call at loop 0, copy path, 3000 x 16 updates, lr 1e-3). Eval wording stays disjoint:
gen2 prunes every frame sharing a sentence or a word 6-gram with any eval frame; `python3 -c "import gen2,json;print(gen2.disjointness_report())"`
reports 0 shared 6-grams, 0 shared sentences, 0 shared names, 0 shared nouns (output saved in results/DISJOINTNESS-REPORT.json).
Paired baseline: copy-only seeds 0-5 already run (results/armBcopy-seed*-rows.json; the pipeline is deterministic per seed, shown by the exact re-run of pooled B).
Seeds 0-5 for arm M.

Noise (standing numbers, 6 seeds): copy-only new-wording right-call rate mean 81.6%, SD 11.9 points; paired gain SD was 21 points for a null change.
HEADLINE: right-call rate on new-wording questions, per seed; gain = arm M minus copy-only, same seed.
PASS: paired mean gain >= +8 points AND the 95% t-interval (n=6, t=2.571) lower bound > 0 AND train-wording right-call mean >= 98% for arm M.
FALSIFIED: paired mean gain < +3 points.
Between: anything else, partial, no claim.
Also reported: arm M SD across seeds (is the spread smaller?), unseen-answer accuracy, final accuracy; per-cell numbers.
Per-question rows (192 x 6 = 1152) are copied back and counted before the box is destroyed.
