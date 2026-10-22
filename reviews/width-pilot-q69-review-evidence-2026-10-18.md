# Q69 review evidence: `learn_probe.py --diary-data` (for the coordinator's code review; DRAFT)

Ruling Q69 asks the review to verify two things: (1) the default is unchanged, and (2) no other hard-coded parent assumption remains. This note gathers the evidence; the review itself is the coordinator's (Q75). Code: 6d8c8d3, tidied in 99cba1a47 (branch `claude/width-pilot-drafts`).

## 1. Default unchanged (shown)

- `--diary-data` defaults to `DIARY_DATA`, the original path; `train(diary_data=DIARY_DATA)` and `build_parent_diary(data=DIARY_DATA)` have the same default. Test: `test_default_is_the_original_path_in_flag_and_in_train`.
- The early check (99cba1a47) only looks at a **given** folder; the default path is not checked, so a default run fails or succeeds exactly as before.
- With `--guard` off, the default is accepted silently as before; a non-default `--diary-data` without `--guard` is refused before any work (it would never be read).
- **Record-only differences:** the run record gains `guard_diary_data`, which is `None` when the diary came from `--diary-cache` (the cache path and the diary's sha256 are recorded beside it). With `--log-update-rms` on, there is also a new `update_rms_secs` timing field. Training is unchanged: the C8 off/on runs are bit-identical (weights, per-update losses, RNG state) on a stand-in parent, including the kfsoft guard path.

## 2. Remaining hard-coded parent assumptions (shown, grep of `learn_probe.py`)

| Constant / site | Used by the join stage? | Status for the pilot |
|---|---|---|
| `PARENT` (s200 checkpoint), default of `train(parent=…)` / `--parent` | Only as a default | Every pilot run passes `--parent <its own parent>`. Inside `train()` every parent use goes through the `parent` argument (checkpoint, model, KL parent, harm function). |
| `PARENT` used directly in `build_mode` (line ~513) | No: a build stage | The L5 rows are already built and hash-frozen (15cda9d3…); no pilot run calls it. |
| `DIARY_DATA` | Yes, the diary pool | **Fixed by `--diary-data`** (this change). |
| `DIARY_LOG` (s200 main-brain log) | Only for the diary comparison | Skipped with `--diary-compare none` (in the pilot command). |
| `DEV_IN_DIST` (another session's `/tmp` path) | Only with `--harm-steps` | Not parent-specific; `--dev` overrides it. If the pilot measures harm, the run card must pass `--dev <seed-1 200k build>/dev/in_dist.jsonl`. |
| `GUARD_CONSTANTS` (`constants-kf99n-lr3e4.json`, "the s200 sheet run's") | Yes: diary size 4096, check 512 | Recipe constants, identical at every width. Not a parent dependency. |

**Answer:** no other hard-coded parent assumption remains on the join-stage path, given `--parent`, `--diary-data` and `--diary-compare none`. One adjacent hard-coded path, `DEV_IN_DIST`, matters only if harm is measured, and it already has a flag (`--dev`).
