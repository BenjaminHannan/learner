# 336b verification: 0.1 + gram-360 fill-in finisher, end to end on bank B (month-end line, 2026-09-25 ~03:40 UTC)

**Verdict: 336b = registered FAIL** on the 336 marks (M1-M11 on arm G), as 336 was. The same 3 marks pass
(M8a, M8b, M8c). **B1 (grammar gain from the finisher) = PASS** with one disclosed deviation (a replacement grader).
**B2 (sleep learned) = FAIL**: sleep's file was present at all 360 sleeps, but sleep attempted to learn 0 times.

Run: handoff task rent-336b, RESULTS-rent.md (origin/builder-outbox). One rented 5090 after one unreachable host;
~$0.66. Seal 229/229 OK, bank SEAL 3/3 OK, twin b banner on every arm, no tracebacks in completed arms. Arms:
G = 330c + gram-360 (registered), P = 330c (control), T = twin b, B = 292t. Marks: PASSMARKS-336b.md, which points to
artifacts/claude-e2e336-20260924/PASSMARKS.md.

## Marks on G (bars fixed before the run)
| Mark | Bar | G result | Verdict |
|---|---|---|---|
| M1 wrong-save turns | ≤ 1 | 35 turns (35 of 181 new triples wrong by both judges; 1 split, third judge ok; 0 nosave turns with writes) | FAIL |
| M2 wrong answers stated as fact | ≤ 1 | 2 of 7 WRONG_CANDIDATE asks (both judges agree on all 7) | FAIL |
| M3 taught facts saved | ≥ 85% | 156/333 = 46.8% | FAIL (−38, "proved wrong" fires again) |
| M4 answerable asks right | ≥ 70% | 39/185 = 21.1% (RIGHT 10 + RIGHT_CONFIRM 29) | FAIL (−49) |
| M5 never-told asks | ≥ 95% | 36/38 = 94.7% | FAIL (by 1 ask) |
| M6 G − T right-rate | ≥ +20 each | two_hop 0.0 (3/37 vs 3/37); reversal +10.7 (5/28 vs 2/28); edit +5.1 (5/39 vs 3/39); abstention +56.9 (36/51 vs 7/51) | FAIL (abstention only passes) |
| M7 grammar, both valid graders | ≥ 99% | 89.1% (483/542, grader A2) and 76.9% (417/542, grader B) | FAIL |
| M8a variety | ≤ 5% | 27/619 = 4.4% | PASS |
| M8b clarify | ≤ 15% | 17/619 = 2.7% | PASS |
| M8c G vs B, blind pairwise | ≥ 36/40 | 38/40 (2 ties, 0 losses) | PASS |
| M9 kept across sleeps/restarts | 100% | 87/90 = 96.7% | FAIL |
| M10 creative | writes 0; unsupported person-facts 0; useful ≥ 80% | writes 0; 17 unsupported person-facts in 12 replies; useful 13/38 = 34% | FAIL (writes pass) |
| M11 speed and attention | median ≤ 3000 ms; p90 ≤ 8000; confirm rows ≤ 1/8 | 756 ms; 1155 ms; 180/619 = 29.1% | FAIL (speed passes, on a 5090) |

M4 denominator: edit 39 + one_hop 63 + reversal 28 + two_hop 37 + yesno 18 = 185. Abstention = never_told 38 +
partial 13 = 51, counted RIGHT + RIGHT_CONFIRM as in 336.

## Extra marks (G vs P)
| Mark | Bar | Result | Verdict |
|---|---|---|---|
| B1 grammar share G − P, each valid grader | ≥ +5 on both | grader A2: 89.1% − 78.8% = +10.3; grader B: 76.9% − 69.0% = +7.9 | PASS (deviation 1) |
| B2 sleep learned | 0 missing checkpoints; attempted ≥ 1 row per arm | checkpoint present 360/360; attempted 0/120 in G, P and B | FAIL |

Grammar packet: 542 distinct G replies and 542 distinct P replies (384 shared, 158 only in each), plus 40 planted
errors and 40 planted clean lines, 780 items, graders blind to arm. On the lines only one arm said: A2 ok 139/158
G-only vs 83/158 P-only; B ok 120/158 G-only vs 77/158 P-only. Validity: A2 caught 39/40 planted errors, kept 40/40
clean; B caught 40/40, kept 38/40.

## Deviations (disclosed)
1. **Grader A was invalid** (caught 24/40 planted errors; the bar for a valid grader is 36). Its reading is not used.
   A replacement blind grader (A2) got the same packet A and the same prompt, word for word, and was valid (39/40).
   Replacing an invalid grader was not written in the marks beforehand. For the record, invalid grader A read
   G 76.2% vs P 71.4% (+4.8), just under the +5 bar; grader B alone would pass B1.
2. The rental needed a second host (the first refused ssh) and two relaunches before any arm output (a missing
   run/ folder for the gram-360 log; missed sleep-check env vars on P). One live process per arm at all times;
   no arm file was written twice (RESULTS-rent.md, deviations).

## What this shows
- **The finisher fixes what it targets (shown).** G and P match on every memory count (G 180 confirm rows vs P 181,
  one sampled difference), so gram-360 changes only text, and both valid graders rate G 8-10 points more grammatical.
  But whole-reply grammar is still 77-89%, far from 99%: most remaining errors are in the 1B's own replies and the
  reader's saved slot values ("pet is alpaca", "your other is ..."). This agrees with the grammar thread's next
  target (the 1B's own replies).
- **Sleep never learns in 0.1 (shown), even with its file present.** Every one of the 360 sleeps says "0 word episodes
  (< 8); kept queued, nothing to gate". Sleep's only learning recipe is for family-word shortcuts, and it waits for 8
  questions that use a new family word (scripts/fable_wire51_adapters.py:286, 383, 513). Ordinary chat never
  produces them. So the "learning over time" row cannot pass with this sleep; the Fix-sleep thread's new sleep
  (365 road map) is the path, and it joins only after its own PASS.
- **Memory is still the blocker (shown).** Saved 47% of taught facts, answered 21% of answerable asks. The judges' reasons
  for the 35 wrong saves: the catch-all relation "other" (11-14 by judge), a count read as an age (3), a wrong person
  or relation, and 4 facts never taught. The reading thread owns this (370); rd-373 targets saves after a confirm.
- **Safety vs the plain twin (report only):** G states a mechanical wrong answer on 7 of 236 memory asks (2 judged
  wrong); the plain twin states one on 194 of 236.
- **P here vs 336's P** (report only; banks A and B differ): saved 46.8% vs 57.2%, answerable right 21.1% vs 21.8%,
  kept 96.7% vs 96.8%, confirm rows 29.1% vs 28.2%. With sleep learning nothing in either run, this is bank-to-bank
  spread, not an effect of sleep.

## Scorer counts, all arms (from RESULTS-rent.md)
| | G | P | T (twin b) | B (292t) |
|---|---|---|---|---|
| asks right (RIGHT + RIGHT_CONFIRM) of 236 | 75 | 75 | 17 | 38 |
| mechanical wrong answers | 7 | 7 | 194 | 2 |
| "not sure" (ABSTAIN) | 128 | 128 | 25 | 196 |
| facts saved / 333 | 156 | 156 | 0 | 1 |
| most common reply / 619 | 27 | 27 | 17 | 312 |
| median ms | 756 | 762 | 346 | 8 |

Judge files, keys and the packet builder: judges/ (verdicts m1_judge1-3, m2_judge1-2, m7_gradeA (invalid), m7_gradeA2,
m7_gradeB, m8c_judge1-4, m10_judge; key_A/key_B carry only planted/in_G/in_P flags; judge_prep336b.py). Packets hold
bank text and stay out of git. Bank B is now spent.
