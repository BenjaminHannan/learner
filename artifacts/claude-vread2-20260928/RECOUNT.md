# vread2 blind recount

Files read: `PASSMARKS.md`, `bar.json`, `scores/A-s327.json`, `scores/B-s327.json`, `scores/A-s331.json`,
`scores/B-s331.json`. Nothing else was opened: no verdict.json, no RESULTS.md, no script. Nothing was run
except small Python reads of these JSON files. Shares use exact fractions; the percents below are rounded
for display only.

## Save bars
Each score file's `bar` equals its `bar.json` entry, and the same bar appears in the file's `main` block:
A-s327 0.85, B-s327 0.90, A-s331 0.90, B-s331 0.85.

## Validity counts (gold block, the same in all 4 files)
- Backref cards: 538. The mark needs at least 200, so it is **met**.
- Backref cards whose owner's name appears 3 or more times: 150. The mark needs at least 60, so it is **met**.
- Bins: 237 cards with 1 copy, 151 with 2, and 150 with 3 or more (total 538).

## Seed 327

| Item | A | B | Mark | Met? |
|---|---|---|---|---|
| Below-0.97 share, 1 copy | 38 of 212 (17.9%) | 30 of 220 (13.6%) | | |
| Below-0.97 share, 3+ copies | 50 of 141 (35.5%) | 11 of 136 (8.1%) | | |
| A repeats the pattern (3+ minus 1 is at least 25 points) | +17.5 points | | ≥ 25 | **no** |
| M1: B's 3+ share minus its 1-copy share is at most 10 points | | −5.5 points | ≤ 10 | yes |
| M2: backref right saves at 0.97 (history rule) | 378 | 432 | B ≥ 378 + 26.9 = 404.9 | yes |
| M3a: wrong turns (whole set, main rule, own bar) | 32 | 33 | B ≤ 34 | yes |
| M3b: backref wrong saves at 0.97 | 7 | 5 | B ≤ 9 | yes |
| Proved-wrong gap: B's 3+ share minus A's | | 27.4 points | ≤ 10 | no |

## Seed 331

| Item | A | B | Mark | Met? |
|---|---|---|---|---|
| Below-0.97 share, 1 copy | 36 of 214 (16.8%) | 33 of 219 (15.1%) | | |
| Below-0.97 share, 3+ copies | 34 of 143 (23.8%) | 17 of 141 (12.1%) | | |
| A repeats the pattern (3+ minus 1 is at least 25 points) | +7.0 points | | ≥ 25 | **no** |
| M1: B's 3+ share minus its 1-copy share is at most 10 points | | −3.0 points | ≤ 10 | yes |
| M2: backref right saves at 0.97 (history rule) | 411 | 437 | B ≥ 411 + 26.9 = 437.9 | **no** (0.9 short) |
| M3a: wrong turns (whole set, main rule, own bar) | 36 | 41 | B ≤ 38 | **no** |
| M3b: backref wrong saves at 0.97 | 11 | 7 | B ≤ 13 | yes |
| Proved-wrong gap: B's 3+ share minus A's | | 11.7 points | ≤ 10 | no |

## Verdict: INCONCLUSIVE

The test only counts if arm A shows the old problem again. The problem was that A is much less sure of the
right owner when the owner's name appears 3 or more times. On vread's old dev reads the gap was 47 points
(19 of 30 against 8 of 49). On the fresh set it is only 17.5 points in seed 327 and 7.0 points in seed 331.
Both are short of the 25 points the marks require, so validity fails in both seeds.

The pass marks and the proved-wrong check therefore do not decide the result. They are listed above for the
record only:
- Seed 327 met M1, M2 and M3.
- Seed 331 met M1 but missed M2 (by 0.9 of a save) and M3 (5 more wrong turns, against an allowance of 2).
  So B would not have passed even if validity had held.
- Proved wrong does not apply, because validity fails. B's 3+ share also moved more than 10 points from A's
  in both seeds.

## Consistency checks
- In every file, the reported `right_owner_low_share_pct` equals low ÷ right-owner exactly.
- In every file, the top-level wrong turns, right saves and wrong saves equal the numbers in the `main` block.
- The top-level backref saves at 0.97 equal the numbers in the `backref_hist_097` block, which ran at
  bar 0.97 under the history rule.
- The lowest-probability counts on right-owner low cards add up to the total of the low bins (114, 61, 88
  and 62).
- In A-s327, B-s327 and A-s331, matched cards minus right-owner cards equals `wrong_person` exactly.
- **One small gap.** In B-s331, matched cards minus right-owner cards is 532 − 499 = 33, but
  `wrong_person` is 30. That leaves 3 matched cards that are neither right-owner nor wrong-person. They may
  be cards whose read owner is "me", which the wrong-person count leaves out by definition. The score files
  alone cannot confirm this. It does not touch any mark.
