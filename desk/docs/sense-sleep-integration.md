# Sleep for the senses: integration note for the lead (T4, 2026-11-04)

**Blocked until the vision projector is plugged into the app** (separate job). Nothing here is wired into main.js yet.

## What is ready
| Part | Where | Tests |
|---|---|---|
| Feature store (encoder features only, float16, never raw), anchored practice + logic check, 2-of-3 rule with direction gate (OFF by default), `maybe`s, seatbelt decision, night ledger with quarantine and replay of kept nights | `desk/src/sense-sleep.js` | `desk/test/sense-sleep.test.js` (8) |
| Projector night for the sleep app: backup, fixed tests before/after on bf16 and q8, train (MLX, bf16), exact byte rollback + quarantine on any drop > 2, crash rollback, Ben-first stop | patch `premonition-sleeplab-t4/phase2/sleepmlx-sense-projector.patch` (new files `sleepmlx/sense_projector.py`, `sleepmlx/tests/test_sense_projector.py`) | 7 unit tests (pure Python), `git apply --check` OK on sleepmlx-src |

Toy evidence: `~/learner-ops/premonition-sleeplab-t4/REPORT.md`. Text-anchored practice, the echo guard and the seatbelt passed.
The 2-of-3 rule and multi-frame video practice did NOT pass, so the 2-of-3 rule ships switched off and nothing special is done for video.

## Wiring, step by step
1. **Day (watching/listening), once the projector is in the app:** after SigLIP2 / Whisper encode a frame or clip for the projector, call
   `new FeatureStore(userData, { isPrivate }).add({ t, clip, frame, source, eye: { encoder: EYE_ID, vec, shape: [64, 768] }, ear: { encoder: EAR_ID, vec, shape }, text: { subtitle, soundTag, screen, caption, title }, ctx: { category } })`.
   - Use `senses.isPrivate` for `isPrivate`. Use the pooled features the projector consumes (64x768 for vision), not the raw image.
   - `EYE_ID` / `EAR_ID` must change whenever the encoder or the pooling changes: features from an old encoder are skipped at night (they must be rebuilt).
   - Caps: 2,000 records and 200 MB per day (about 2,000 frames at 98 KB each). Call `prune(keepDays, now, ledger.pinnedDays())` nightly.
2. **Night, before the brain sleep or after it (benFirst: only when Ben is not chatting):**
   - `buildPractice(store.records(day), { encoders: { eye: EYE_ID, ear: EAR_ID }, logicCheck })`.
     `logicCheck(text, record)` should be the Nanbeige "does this make sense" check; the default is a rule-based stand-in (`maybe` never trains; the text's category must fit the title).
   - Leave `twoOfThree` off (toy: not proven, wolf/dog confusion rose in 1 of 3 toy worlds). To try it later, also pass `guesses` (each sense's own description per record), `agree` and `fitsContext`.
   - `ledger.writeManifest(night, practice, { encoders })` → `userData/sense-sleep/practice-<night>.json`.
3. **Sleep app** (after the patch is applied): for each sense with practice,
   `sense_projector.run_night(weights, manifest, train_fn=make_mlx_train_fn(lm_loss), eval_fn=bf16_fixed_tests, q8_eval_fn=q8_fixed_tests, should_stop=ben_is_chatting)`.
   - `lm_loss(projector, x, caption)`: the caption's next-token loss from the **bf16** Nanbeige copy (frozen) with the projector output spliced in (`premonition-projectors/mlx_projector.py` `splice`, same prompt as training).
   - `bf16_fixed_tests` / `q8_fixed_tests`: V1 / A1 / VID1 from `premonition-projectors` (top-1 of 10). A drop > 2 on **any** of them, on bf16 **or** q8, undoes the night (exact bytes; checked by sha256) and quarantines its practice.
   - The ledger line goes to `sense-sleep/nights.jsonl`, the same file the Desk's `NightLedger` reads; the morning summary can show `kept`, `reason`, `drops`.
   - Disk: the bf16 Nanbeige copy needs ~8 GB more (design section 9).
4. **Morning:** the app loads the (kept) projector next to the q8 Nanbeige as today.

## Not done / not tested
- `make_mlx_train_fn` ran only on a tiny fake loss (bf16 output checked). It has never trained against a real model (none was loaded).
- No real-path check: whether one night of caption-tagged sound pairs gives A1 +5 (design section 9's first real test) is untested.
  In the toy the ears were limited by data. The real sound projector looked limited by the **encoder** (6.5x more data did not move A1),
  so the toy gain may not carry over to real sound until the encoder is swapped.
