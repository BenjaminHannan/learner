# Lead 0 marks (diagnostic, not a race entry). Sealed 2026-09-28 21:49 UTC, before any run.

**Question.** Is the jumpiness of the few-example curve across k just the learning rate?
**Change.** Only the AdamW learning rate of the adaptation Learner. Everything else is the sealed eq harness: same source net, pool, batches, 2,048 updates, dev 9x9 panel of 300 (`scripts/claude_dir_lr_lead0.py` imports it, edits nothing). No sleep, no holdout, no old panels.
**Runs (main).** Practised loop, seed 1 (source `runs/qual-loop-s1`), k = 1,024 and 16,384, lr in {3e-4, 1e-3, 3e-3}: 6 counts of 300. The 1e-3 rows are a rerun of the stored baseline (233 and 261 of 300, `eq-runs/loop-s1-pre/adapt.json`); if the rerun differs, the ruler is not bit-reproducible on the run machine, and that difference is itself the same-start noise (reported, not hidden).
**Runs (extra, same rules).** Fresh loop, seed 1, same 6. Reason: the collapse (0 of 300 at k=1,024, then 128, then 18) is in the *fresh* loop; the practised loop's stored dev curve is 173, 277, 233, 292, 261 for k = 64..16,384, which wobbles by about 60 counts but never collapses.

**Bars (fixed now).** Counts of 300. One count is 0.33 points; the counting SE of a difference of two 300-maze scores is about 12 counts near 50%, so **30 counts (10 points)** is about 2.5 SE, and above the largest same-start seed gap in F_eq (2.5 points, NOISE.md) as a per-rung bar.
- A rung is **lr-sensitive** if max minus min over the three lrs is >= 30 counts.
- Practised loop word: **LR_MATTERS** (both rungs lr-sensitive), **LR_MATTERS_AT_ONE_RUNG**, or **NOT_THE_LR** (neither). 
- Result that would prove the lr suspicion wrong: **NOT_THE_LR** on the practised loop (spread under 30 at both rungs) **and** no lr rescues the fresh loop's k=1,024 collapse to >= 60 of 300.
- Fresh loop extra: "rescued" if any lr gives >= 60 of 300 at k=1,024 (stored 0).
- Only 2 rungs and 1 seed, so this is a diagnostic: it can say "the lr moves this curve" (**shown**, for that net and seed) or "not shown"; it cannot say the lr explains the whole jumpiness elsewhere (**untested**).

**What the answer changes.** LR_MATTERS: every later comparison must fix or sweep lr for both arms of the pair, and the stage-two win/loss reads only at the winning lr. NOT_THE_LR: the jumpiness is not the lr; keep 1e-3.

**Self-check (common brief).** (1) Bar 30 counts sits above counting noise (~12 counts) and the noise in NOISE.md (max same-start F_eq gap 2.5 points). (2) Only two words, no rejection wording: "not shown" is the default. (3) Comparator is the stored same-start baseline plus a rerun of it. (4) Plain-net row: n/a for a diagnostic (no promotion claim). (5) F_few: n/a here; Lead 1 has it. (6) No sleep gate.
