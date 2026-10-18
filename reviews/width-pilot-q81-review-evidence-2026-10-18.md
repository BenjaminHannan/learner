# Q81 review evidence: the three checks on fix commit 99cba1a47 (for the coordinator's consolidated review; DRAFT)

Ruling Q81 points the Q75 review at 99cba1a47 and names three checks. This note gathers the evidence; the review itself is the coordinator's.

## 1. The 49 tests (shown)

`python3 -m pytest domain/far/test_learn_probe_c8.py domain/far/test_learn_probe_diary_data.py domain/far/test_learn_probe_r1.py custom_io/tests/test_update_rms.py custom_io/tests/test_pilot_bars.py -q` gives **49 passed** at 99cba1a47.
- Known: `test_flag_off_matches_original_loop` failed once on the first run after the edit, then passed 8 of 8 reruns; the pre-fix code passed 6 of 6. No cause found. It is reported, not hidden.
- Fixed in the same commit: an order dependence in the diary-data tests. After the c8 suite, a cached `mainbrain` import broke them; this also happened on the pre-fix code.

## 2. pilot_bars moves no written bar value (shown, `git diff 99cba1a47~1 99cba1a47`)

- **Spec values:** the example spec's only change is the added `"extras": ["pass_count"]` line. The gate value (8.0), rule values (8, 2, 2, 6, 4, 8), floor_sd (3.0), alpha (0.05) and the default are untouched.
- **Code:** the one change to how a condition is evaluated is `OPS[op](actual, value)` → `OPS[op](round(actual, 9), round(value, 9))`, the same 9-digit rounding the report already prints. It changes a verdict only when the statistic is within about 5e-10 of a bar, which is float error, not data. Test: `test_value_on_the_bar_holds_despite_float_error`.
- **The other changes are refusals:** a spec naming an unknown variable is rejected, and the CLI exits 2 when a missing variable could have changed the verdict. No threshold, statistic or rule order changed.
- The sealed spec is not written yet. When it is, it must list any extra scalars in `extras`.

## 3. The C8 timing exclusion does not alter training steps (shown)

- **Flag off:** `rms_s` / `rms_secs` stay 0.0 and no sync is added. The off-vs-original and off-vs-on tests are bit-identical on weights, per-update losses and RNG state, in both trainers, including the kfsoft guard path.
- **Flag on, join stage (`learn_probe.py`):** the lr is constant (1e-4), the update count is fixed (4,000), and nothing reads the clock to pick a step. The timing change moves only `train_secs`, the s/update print and the new `update_rms_secs` field.
- **Flag on, parent stage (`custom_io/train.py`):** the clock affects training only through `elapsed` when `--minutes` is set. That covers the lr progress and the time-cap stop. The frozen parent recipe (amendment §A: `--steps 24000 … --log-every 500`) sets no `--minutes`, so the lr follows step count and steps are unchanged. With `--minutes` set, excluding C8 time makes a flag-on run's schedule closer to flag-off, not further.
- Item 1 should still time with the flag in its recorded state and report `update_rms_s` beside `train_s`.
