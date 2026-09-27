# Exp 252c RESULTS (merge 252b + 258 + 259): registered verdict FAIL, exactly as predicted

Agent: scripts/claude_loop252c_agent.py + artifacts/claude-merge252c-20260922/loop252c-config.json.
Seal: artifacts/claude-merge252c-20260922/SEAL.sha256.txt (9 files, all OK on re-check 2026-09-22 19:59).
Panel seals re-checked OK before the runs: artifacts/claude-corrpanel252-20260922/SEAL.sha256.txt,
artifacts/claude-corrtail258-20260922/SEAL.sha256.txt.
Runs: M2, M3, M5–M8 were already registered by the previous agent (outputs in run/, not re-run).
M4 (corrpanel252) and M1 (corrtail258) each run ONCE with the sealed driver
scripts/claude_merge252c_runall.sh (stages m4, m1) and the sealed scorer
scripts/claude_merge252c_score.py. No new scorer was written. No item text is quoted below.

## Verdict

**Registered verdict: FAIL** — exactly the FAIL predicted in PASSMARKS.md (P252c.1–.5 all correct).
Two pre-declared known gaps, neither caused by the merge:
1. M1: bar "no wrong value on 252c where 258 or 259 had none" missed at exactly one id, t258-026.
2. M3: junk on exactly two ids, d258-037 and v259-008 (both are junk in the own arms too).
Every other bar on every mark passes, and every move matches the sealed predictions with 0 unpredicted,
0 missing and 0 off-record rows.

## Marks table (integer counts)

| Mark | Bar | Result |
|---|---|---|
| M1 corrtail258 (80) | every item right on 258 or 259 right on 252c | PASS (0 lost) |
| M1 | 0 false claims /80 | PASS (0) |
| M1 | 0 junk /80 | PASS (0) |
| M1 | no wrong value where 258/259 had none | **FAIL (1: t258-026)** |
| M1 | keep 8/8 + control 16/16 byte-identical | PASS (8, 16) |
| M1 | question_tail 6/6, unstored_tail 6/6 | PASS (6, 6) |
| M2 dev252b | 0 junk / 0 false / 0 wrong removals / 0 question writes; controls identical; 31 exact moves | PASS |
| M3 dev258 (79) + dev259 (66) | own-arm records except sealed exceptions; 0 false replies; 0 junk | **FAIL on junk only: d258-037, v259-008** |
| M4 corrpanel252 (100) | moves exactly per sealed rule; 0 new wrong/junk/false | PASS (only c252-022) |
| M5 suites | moves = 252b's; 0 new WRONG/WRONG-WRITE/junk/lost OK | PASS (rt136 4, rt143 0, sessions152 1, bench 0) |
| M6 smoke | identical to smoke-252b.json except labels/paths/timing | PASS (0 differences) |
| M7 restart (18 rows) | 0 ghosts, 0 dup fails, replies = 252b's except predicted | PASS (0/0/0) |
| M8 latency | median added/turn <= +5 ms vs 252b | PASS (-0.11 ms) |

## M1 side by side: 252b, 258, 259, 252c (counts from the sealed scorer)

Right per family (denominators: 12, 12, 10, 10, 8, 6, 6, 16; total 80):

| Family | 252b | 258 | 259 | 252c |
|---|---|---|---|---|
| that_denial | 0 | 7 | 3 | 7 |
| that_correction | 0 | 3 | 0 | 3 |
| pure_denial_that | 2 | 6 | 2 | 6 |
| other_tail_denial | 1 | 1 | 2 | 2 |
| keep | 8 | 8 | 8 | 8 |
| question_tail | 6 | 6 | 6 | 6 |
| unstored_tail | 6 | 6 | 6 | 6 |
| control | 16 | 16 | 16 | 16 |
| **Total right** | **39** | **53** | **43** | **54** |
| false claims | 5 | 1 | 1 | 0 |
| junk writes | 2 | 0 | 2 | 0 |
| wrong values | 40 | 27 | 36 | 26 |

Moves vs 252b on 252c (24 ids, all predicted, each equals 258's registered row except
t258-035 which equals 259's; not_as_predicted empty):
t258-001, 002, 003, 008, 009, 010, 011, 013, 015, 016, 019, 023, 024, 025, 026, 027,
029, 030, 031, 033, 034, 035, 059, 064.
Became right vs 252b (15 ids):
t258-001, 002, 003, 008, 009, 010, 011, 013, 019, 024, 025, 031, 033, 034, 035.
Became wrong vs 252b (0 ids): none.
Moved but still wrong (9 ids): t258-015, 016, 023, 026, 027, 029, 030, 059, 064.
New wrong value where 258/259 had none (1 id): t258-026 (predicted; the merge keeps the
stored value and says it, where 259 avoided it only by writing a junk value).
Lost vs 258-or-259 (0 ids): none. 252c right (54) = every item right on 258 or 259, plus
t258-035 from 259's side; no item right on either arm is wrong on 252c.

## Every move by id, all marks

- M2 dev252b (31 moved, unpredicted 0, missing 0, off-record 0):
  b252-001, 002, 003, 004, 005, 006, 007, 008, 010, 011, 013, 014, 015, 016, 017, 018,
  019, 020, 021, 023, 024, 026, 027, 029, 030, 031, 032, 033, 035, 036, 037.
  Junk 0, wrong removals 0, question writes 0, control diffs 0, false replies 0 on 252c
  (252b itself had false replies on b252-001, 003, 010, 013, 014, 015 — all gone on 252c).
  Second scorer (252b's own): PASS.
- M3 dev258 (79 rows): differs from 258's own arm on exactly the 2 predicted exceptions
  d258-003, d258-039 (both equal the same-session 259 arm). Junk: d258-037 only, also junk
  in 258's own arm (predicted known gap). False replies 0.
- M3 dev259 (66 rows): differs from 259's own arm on exactly the 12 predicted exceptions
  v259-010, 011, 012, 015, 016, 029, 035, 037, 038, 058, 059, 063 (all equal the
  same-session 258 arm). Junk: v259-008 only, also junk in 259's own arm (predicted known
  gap). False replies 0. Keep items identical to own arm on both sets.
- M4 corrpanel252 (100 rows): moved exactly 1 id, c252-022, class "both" — the sealed rule
  confirms a clean removal of exactly one stored triple (Tobin), reply starting
  "OK, I removed Tobin as ", stores stable at followup. All other 99 rows byte-identical
  to 252b. New wrong values 0, new junk 0, false replies 0 on 252c (252b had a false reply
  on c252-022 — gone on 252c). PASS.
- M5 suites: move counts equal 252b's (rt136 4, rt143 0, sessions152 1, bench 0);
  0 new WRONG, 0 new WRONG-WRITE, 0 new junk; all rows equal except seconds. Second scorer
  (258's): all four suites same_as_252b on every field. PASS.
- M6 smoke: 0 differences, identical true. PASS.
- M7 restart dialogs: 18 rows each file; ghosts 0/0, failed duplicate checks 0/0,
  reply moves 0. PASS.
- M8 latency: base median 2.76 ms, 252c median 2.65 ms, added -0.11 ms (bar <= +5 ms). PASS.

## Misses (3 total, all predicted before the seal)

1. t258-026 (M1): wrong value on 252c where 259 had none (259's row avoided the wrong value
   only by writing the junk value "stale"; 252c writes no junk and keeps the stored value).
2. d258-037 (M3 dev258): ", sadly" stored as the value by 252's two-clause path — same in
   258's own arm and in 252b. Out of scope of both pieces.
3. v259-008 (M3 dev259): same ", sadly" cause — same in 259's own arm and in 252b.

## Deviations

None. M4 and M1 were each run exactly once, after the seal, with the sealed driver and
sealed scorer; the driver re-verified the corrtail258 panel seal before M1 (all OK).
M2, M3, M5–M8 were not re-run (registered outputs and sealed scorer verdicts confirmed
from run/). No sealed file was changed (all three SEAL checks fully OK). No new scorer was
written. The design note design/v3/30-modes/252c-merge-opus.md already existed, so per the
brief no new copy was written. Machine load stayed under the gate (peaks ~16, gate 60);
free disk stayed at 5 GB (stop bar 3 GB). Ledger outcome line P252c.6 appended.

## What it means (plain English)

The merge works as designed. The two fixes stack: 252c keeps every fix from 258 (53 right
on the tail panel) and adds 259's one unique fix, reaching 54/80 with zero false claims and
zero junk writes, while the base had 5 false claims and 2 junk writes. The one new removal
(c252-022) is exactly the case the director said needs both pieces together, and nothing
else changed on that panel. All safety marks (suites, smoke, restarts, speed) pass
unchanged. The 3 misses are old, known gaps written down before the seal — the merge
creates no new problem.

## What it doesn't mean

It does not mean the correction line is finished: 26 of 80 tail-panel items still give a
wrong value, and the ", sadly" two-clause junk (d258-037, v259-008) plus t258-026 are still
open. It does not mean 252c is better than 258 everywhere: on this panel 252c (54) is only
1 above 258 (53). It says nothing about blind panels — M1 here was a known-set regression
check, and M4 was scored by a mechanical rule, not by reading new behavior.
