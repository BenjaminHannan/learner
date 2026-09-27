# Baseline validity and reporting marks

Sealed 2026-09-27 22:36 UTC before any baseline run. No mark changes after maze panels are seen.

- **V1 source guard:** each source-trained net, separately for seeds 0 and 1 and loop and plain, gets at least 190 of 200 on fresh 4-digit sums and at least 190 of 200 on fresh 5×5 Latin grids before maze adaptation. A failing arm is ineligible; the ruler is invalid if any source-trained arm fails.
- **V2 live gradients:** in an fp32 CPU one-step check without autocast, every two-dimensional weight matrix in each source-trained model has a nonzero gradient on at least one of a sums batch and a grids batch. Any matrix with zero or absent gradients on both invalidates that arm and the ruler. Report matrix counts and the missing names.
- **V3 usable ladder:** on the 9×9 **dev** panel, at least one of the four arms in at least one seed must have accuracy strictly above 10% and strictly below 90% on at least three of the nine positive rungs. If not, report **INCONCLUSIVE**, stop, and never tune against the holdout.

If V1–V3 pass, the baseline result is descriptive, with no extra win gate. `F_all` uses the nine positive holdout rungs. Report paired seed results and differences; do not pool seeds to turn a one-seed win into a two-seed claim. Report all `x of n`, source scores, old scores after k=64 and after 64k, both sleep D values by kind, fixed-depth versus learned-stop gaps, mean rounds, cap hits, weight and persistent-coefficient counts, optimizer updates, raw-memory allowance, training time, and distinct layout counts. The 50%-after-64 line is report-only. Labels in the interpretation: **shown**, **suggested**, or **untested**.
