# V1_PARAMS amendment 1 (2026-10-21, before any arm or Gate S run; V1_PARAMS.md itself is unchanged, hash in PARAMS-HASH.txt)

Made after the blocking-only review round. No bar, threshold, budget or spec line changes: these fix HOW a stated rule is measured or make a stated component actually run.

1. **A1 measurement.** The "running median" is taken over the previous 200 steps of the same curriculum phase (gold / teacher / own), because the loss changes definition between phases; the 1% is still counted over all steps so far (needs >= 300).
2. **A4 measurement.** Spend = elapsed wall-clock of the arm (summed over restarts, persisted in `spend.json`) x the box $/h, checked at every wake step and at every sleep stage boundary. The arm jobs always pass `--price-per-hour` and `--spend-cap`.
3. **Judging after a stop.** After A1-A4, `v1/run.py` restores the last good checkpoint, writes `D-final.pt` and `final_dev.json` (marked `aborted`), using the latest finished creative stage (W2 > W1 > N' > warm-up). A rerun refuses while `ABORT.json` exists unless `--ack-abort` (a recorded deviation); `--relaunch-adamw` is the FULL arm's single A1 relaunch (last good checkpoint, plain AdamW). A3 is re-applied to finished stages on a restart.
4. **The sealed creative file.** `creative/stones.py` no longer reads `creative/data/c2/test.jsonl` (it used only the (kind, params) rule keys to keep stepping-stone rules disjoint). Verified once on rule keys only: the 100 keys of the union of warm/dev/pool/labelled equal the 100 keys that included test, so nothing changed.
5. **Bridge summaries** are divided by their RMS when read (the creative registers have norm ~340, D's states ~11), so the zero-initialised projections see unit-scale inputs.
6. **Wake creative replay rows** are drawn from all 200,000 skills rows (the file is stage-ordered; the first draft used the first 20,000 only).
7. **Code shipping.** `v1/rent.py pack` (all code directories, the tokenizer, the pattern bank and the data hashes) is the mechanism the rental jobs use; `v1/pack.sh` lists the same directories.
