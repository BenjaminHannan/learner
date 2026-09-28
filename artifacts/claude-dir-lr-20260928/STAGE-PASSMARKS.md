# Lead 1 marks: staged unfreeze at adaptation. Sealed 2026-09-28 21:49 UTC, before any staged run.

**One change.** During adaptation only, for the first 25% of the 2,048 maze updates (512 updates = 128 batches, exactly) only the output head (`head.*`) and the stop head (`halt.*`, loop only; it gets no maze loss, so in practice only `head.*` moves) may train; then every weight trains as before. Same rule for fresh, plain and practised nets. Plug-in `scripts/claude_dir_lr_stage_net.py` (a Learner subclass); the sealed harness, source nets, pool, batches, lr (1e-3 loop; source-chosen plain), optimizer, warm-up, clip and sleep are unchanged. Run through the sealed harness's `--plugin` and `--out`.
**Runs.** 8 dev runs: {practised, fresh} x {loop, plain} x seeds {0, 1}, into `artifacts/claude-dir-lr-20260928/stage-runs/<arm>-s<seed>-<init>/`. Comparator: the stored unstaged run of the same start and seed, `artifacts/claude-fewex-20260927/eq-runs/` (Lead 0's 1e-3 rerun says whether it reproduces).
**Score.** Dev, 9x9, learned stop. `F_eq` = mean of the 8 rungs (k=1..16,384); `F_few` = mean of k = 1, 4, 16, 64. Delta = staged minus unstaged, per seed, in points. Seeds never pooled.

**Bars (fixed now).** **F_eq +8.0** and **F_few +10.5** points, both seeds (NOISE.md: the all-starts rung recipe gives 3.96 and 5.23; bars are 2x). Words per row: **HELPS** = Delta >= bar in both seeds; **HURTS** = Delta <= -bar in both seeds; otherwise **NOT SHOWN** (both Deltas printed). **REJECTED** only if the practised loop HURTS F_eq in both seeds (every-seed reading); anything short of HELPS and not that is "not shown".

**Required rows for PROMOTE (all four, both seeds), practised loop:**
1. F_eq Delta >= +8.0.
2. F_few Delta >= +10.5 (its own row beside F_eq; F_few is not folded into F_eq).
3. Plain-net row (a same-size plain net cannot pass it by unfreezing alone): staged practised loop F_eq minus staged practised plain F_eq >= +8.0. Plain gets the identical staging.
4. Carry-over / not-memorising row: staged practised loop F_eq minus staged fresh loop F_eq >= +8.0 (fresh gets the identical staging). Panel layouts do not overlap the support (harness records `support_panel_overlap`, must be 0 of the support set).
The other starts' Deltas (fresh loop, plain) are reported, not gated.

**Result that would prove it wrong.** Practised-loop F_eq Delta below +8.0 in either seed: no gain shown. Below -8.0 in both: rejected. (Lead 1's research chance guess was 20%; untested.)
**Holdout.** Only if dev gives PROMOTE, once per arm and seed with the harness's own `holdout` command, same bars against the stored baseline holdout. Never otherwise; never read before dev is committed.
**Sleep.** Unchanged and not a gate. The harness's single sleep draw per rung is reported descriptively only, not used for any word. A sleep claim would need the mean of 3 draws with margin max(6, 2 x SE) and is not made here.
**Report tool.** `scripts/claude_dir_lr_stage_report.py dev` (selftest included) prints exactly these words from raw JSON.

**Self-check (common brief, in the file).**
1. Bars above noise: F_eq +8.0 > 3.96 (all-starts rung recipe), and > direct same-start gaps (max 2.12 dev); F_few +10.5 > 5.23 and > the largest direct F_few seed gap (8.75, fresh loop). Source: NOISE.md / noise-from-raw.txt.
2. Every-seed reading: REJECTED needs HURTS in both seeds; a non-win is "not shown".
3. Comparator: same-start unstaged baseline. The practised loop (51.21 / 51.67 dev F_eq) already beats every plain start, so it is the higher loop; no loop-with-episodes exists in this test.
4. Plain-net row 3 and fresh-loop row 4 above, both with identical staging; overlap check named.
5. F_few is row 2, required on its own.
6. Sleep: no sleep gate (stated above).
