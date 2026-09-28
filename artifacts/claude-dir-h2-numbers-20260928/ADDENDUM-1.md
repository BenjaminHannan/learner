# ADDENDUM-1 to PASSMARKS.md (numbers puzzles, wide practice pool): H2-a, H2-b, H2-c

Written 2026-09-28 20:52 UTC (`date -u`) by Director helper H10, on the Director's decision, from the adversarial review
`artifacts/claude-dir-h8-review-20260928/REVIEW.md` section 3.5. New file; PASSMARKS.md, DESIGN.md, `SEAL-h2.sha256.txt` and the scripts it
lists are not edited. **The 30-of-300 bar on held-out numbers4, the 8-of-300 proved-wrong line and every other threshold stay as sealed.**

**Order (checked 20:51 UTC):** written before any score of this test was seen. On origin/main (commit d0a10db78) this folder holds only
DESIGN.md, PASSMARKS.md, SEAL-h2.sha256.txt, queue-h2-a.md and queue-h2-b.md; no tests.json, extra.json, train_log or VERIFY file. origin/builder-outbox has
no file under this folder. The job `dir-h2-a` is running (BensPC); I cannot see its local files (untested) and have seen no score of it.
The floor in (b) is computed from code and the sealed dev pairs alone; no net was read or run.

## (a) Wording of a PASS (supersedes the plain-words idea in PASSMARKS.md lines 8-10 and "35 times fewer repeats", line 26)
The single change moves two things at once: how often each item repeats (69.6 draws per (hand, target) pair instead of 2,410 per hand) **and** how
many different targets each hand is practised with (target 24 falls from 100% to 1,062 of 36,782 pairs, 2.9%, of the numbers4 practice; SHOWN by
PASSMARKS.md lines 26 and 31). So:
- A PASS (PASS-LOOP or PASS-PLAIN) is worded exactly **"a much larger (hand, target) pool fixes it"**. It is never worded "fewer repeats fixed it",
  "repeats were the cause", or "target variety was the cause".
- What this test cannot say (label: untested): whether the repeats, the extra targets, or both did it. The split test, not run here and not proposed
  as part of this test: the old target-24 pool with 1/35 of the numbers4 draws (the same 69.6 draws per hand). If that still memorises or underfits,
  repeats alone are not the lever.
- The proved-wrong wording is unchanged and also names the pool, not the repeat count: "WRONG (a much larger (hand, target) pool did not help)".
- Also fixed in words (SHOWN from `scripts/claude_dir_h2_pool.py`): the pool uses every 4-number hand of 1-13 except the 300 held-out ones, so P_other
  (below) is measured on **hands the net has seen at other targets**, with a target it has not seen for that hand. It is evidence about unseen
  targets, not about unseen hands; the held-out numbers4 score is the only mark about unseen hands.

## (b) The code-only no-search floor on P_other, and the P_other bars against it
Computed now, pure python, no net: `python3 -B scripts/claude_dir_h10_h2_floor.py` (about 95 s here) writes
`artifacts/claude-dir-h10-addenda-20260928/h2-pother-floor.json`. It uses the sealed 300 dev pairs (`claude_dir_h2_pool.split_dev`, seed 41707) and the
diagnosis's own strategies (`scripts/claude_numbers_diag_answers.py`, floors A to C), evaluated exactly over all number orders, any valid answer counts
(as the test does). Expected right answers out of 300 for a strategy that never checks arithmetic:

| strategy (no search, no arithmetic) | expected of 300 |
|---|---:|
| A: random well-formed answer with the right four numbers | 2.21 |
| C: skeleton drawn from the stored-answer frequencies of the new practice pool, random number order | 4.12 |
| B: the single commonest stored skeleton (a b + c d - -, the same skeleton in the old and the new pool), random number order | 12.00 |
| **F: the best single fixed skeleton, chosen after seeing the dev pairs (an oracle; a strict ceiling for "copy one skeleton, never check")** | **12.00** |
| G (report only, not a no-search strategy): the best skeleton for each pair is known, only the order is guessed | 66.38 |

Why B equals F: the skeleton a b + c - d + computes the same value as the commonest one (a + b - (c - d) = a + b - c + d), so both hit the same
share of pairs. For comparison, the target-24 floors in the diagnosis (B = 7.50 on the held-out hands) do not carry over: easy targets are much
easier. In the 300 dev pairs, 11 have a target equal to the sum of the four numbers (any order of an all-plus answer works).

How the sealed P_other bars sit against this floor (they are **not changed**):
- "memorised again" needs P_other ≤ 8 of 300 on every net. 8 is below F = 12.0: a net at or below 8 is no better than a net that copies one fixed
  skeleton and never checks arithmetic.
- "too little target 24" needs P_other ≥ 30 on both seeds of at least one arm. 30 is 18 above F (2.5 times F). It is still below G = 66.4, so a P_other of
  30 to 66 does not by itself show that the net orders numbers by arithmetic; it shows the net beats every no-arithmetic single-skeleton strategy.
- A P_other from 9 to 29 is inside the no-search noise band: it supports neither branch.
No new mark is added; this is how the two existing bars are to be read.

## (c) Practice exactness 0.5 to 0.9 (restates the sealed text; changes nothing)
PASSMARKS.md lines 76-79: "memorised again" needs practice exactness ≥ 0.9 **and** P_other ≤ 8 on every net; "cannot fit" needs exactness < 0.5 on any
net with numbers4 ≤ 8. A net with practice exactness from 0.5 up to (not including) 0.9 is in neither WRONG branch. If any primary net is there, and
the run is not PASS, the result is **PARTIAL** (PASSMARKS.md lines 87-88): no claim, no second change until the Director reads the marks.

## Not changed
PASS-LOOP and PASS-PLAIN thresholds (numbers4 ≥ 30 of 300 per net, gates 295 / 295 / 285 / 275), V0 to V3, the WRONG threshold (≤ 8), the seeds, the pool,
the replication rule (seeds 15 and 16 cannot overturn a primary WRONG), the tests, and the reported-only measures.

## What I could not test
The floors are expectations under stated strategies, computed exactly from the sealed dev pairs; they are not a measurement of any net. Files:
`scripts/claude_dir_h10_h2_floor.py` (run once here, exit 0, unrounded values in the JSON), `artifacts/claude-dir-h10-addenda-20260928/h2-pother-floor.json`.
