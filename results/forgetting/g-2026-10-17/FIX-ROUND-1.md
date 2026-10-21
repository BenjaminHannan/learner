# Fix round 1 for CODE-REVIEW-87e0c0971.md (coordinator GO, Oct 20; $0; no new training runs)

Off path unchanged: with --replay-priority off, 3-update runs of the G1 config (KL 30) and the G3 config (energy 0.999) give
final checkpoints identical to 62cf9ac36's (sha256 3e5c13359bd13e00 and b1b93cbf11436d7a, old == new). The G1/G3 numbers stay valid.
H1's FAIL stands as recorded; H1 was not re-run.

| # | finding | fix | test |
|---|---|---|---|
| 1 (a) | e0_score.py: the 6,800-DEV identity check was always true | `check_devs` asserts the sha256 of BOTH DEV files (1,360: f975d9fb..., 6,800: 3e3a5edb...) before any model loads; any other file stops with SystemExit | results/forgetting/e0/test_e0_score.py: a mismatched big DEV, a mismatched small DEV and a same-length 6,800-row file are each refused |
| 2 | diary_families: no label-file check, silent '?' rows | every diary row must be found in train.jsonl or the run stops (SystemExit with the count); returns the train.jsonl sha256, which every record carries as `replay_priority_labels_sha256` | test_diary_families_real_lookup (no stub) |
| 3 (b) | a NaN KL crashed `choice` | replay_priority_probs counts a non-finite or negative KL as 0 (uniform when nothing is left), so p is always finite; measure_family_kl returns the raw value and the loop prints the non-finite families | test_replay_priority_probs: NaN / inf / -1 give finite p summing to 1; all-NaN gives uniform and `choice` runs; measure test returns NaN as measured |
| 4 (b) | priority ON drew differently from the control from update 1 | p starts as None, so the draw is the control's `randint` until the first measurement and `choice` only after | end-to-end test: ON's draws are randint, choice, choice; its first draw equals the control's |
| 5 | dead post-loop `extra.update` | removed; `replay_priority_measures` now rides on every record via ex() | end-to-end test: measures 0 at step 0 and 2 at step 3 |
| 6 | no minimum family size | REPLAY_PRIORITY_MIN_ROWS = 8: a family with fewer diary rows gets no priority mass (the uniform part only) | test_replay_priority_probs: a 2-row family with KL 100 gets only (1-f)/N |
| 7 | the real label lookup was untested | new test of diary_families without a stub (first-row-wins, sha, unlabelled rows and missing file refused) | test_diary_families_real_lookup |
| 8 | E0 final-checkpoint fallback was a partial copy of analyze.py | `final_checkpoint_of` follows domain/analyze.py: every night 1..N must exist (SystemExit naming the missing ones), fallback to night_N with a note, a note when the summary path differs | test_e0_score.py: missing night, fallback note, path-differs note, clean case |
| 9 | per-family KL forwards in tiny batches | families under the 8-row floor are no longer measured (their KL is unused). Batching across families is not possible without forking Main brain's replay_kl, which returns one mean per batch. Measured cost on H1: 1,066 s of 41,074 s train (2.6%) | measure test: a 7-row family is skipped |
