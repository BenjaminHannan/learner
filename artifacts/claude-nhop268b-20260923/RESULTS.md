# Exp 268b results: n-hop direction guard on 138nb

## Result first

**FAIL** — on M1 only, and on two clauses of M1's bar 1: `bug` is 11/16
right on 268b (bar: ≥ 14/16 with the "(worked out backwards)" label)
with 1 wrong (bar: 0). Every other clause of every mark passes,
including all 44 non-bug panel items byte-identical to 138nb and 0
question writes on both arms. One run per arm; sealed files unchanged
(seal re-checked OK after all runs: 23/23). No silent re-runs. One
diagnosis note below.

## Marks table (integer counts; 138nb's number beside every figure)

| mark | 138nb | 268b | bar | verdict |
|---|---|---|---|---|
| M1 bug right /16 | 0 | 11 | ≥ 14 | **FAIL** |
| M1 bug wrong /16 | 16 | 1 | 0 | **FAIL** |
| M1 bug miss (honest non-answer) /16 | 0 | 4 | rest abstains | info |
| M1 reverse_nochain right /10 | 10 | 10 | identical | pass |
| M1 forward_chain right /12 | 12 | 12 | identical | pass |
| M1 forward_1hop right /10 | 10 | 10 | identical | pass |
| M1 uncued_reverse right /6 | 6 | 6 | identical | pass |
| M1 abstain right /6 | 6 | 6 | identical | pass |
| M1 non-bug rows byte-identical /44 | — | 44 | identical | pass |
| M1 wrong over all 60 | 16 | 1 | — (0 on bug) | FAIL (see bug) |
| M1 question writes over all 60 | 0 | 0 | 0 | pass |
| DEV moves 138nb→268b (predicted list) | — | 46/46 exact | exactly predicted | pass |
| DEV+SUPP+NEW teach/triple changes | — | 0 | 0 | pass |
| DEV new wrong values | — | 0 | 0 | pass |
| M2 invpanel moves 138nb→268b /70 | — | 0 | [] | pass |
| M2 invpanel new wrong | — | 0 | 0 | pass |
| M2 invpanel lost right (of 69 right on 138nb) | — | 0 | 0 | pass |
| M2 invpanel question writes (268b) | — | 4 (teach_control, same as 138nb) | * | pass w/ miss |
| M3 sessions152/bench/marks123 moves | — | 0/0/0 | 0 | pass |
| M3 GATE | — | clean | clean | pass |
| M3 rt136 labels | — | C019–C031 + C076 + C079 + C115 (16) | exactly | pass |
| M3 rt136 direct rows vs 138nb (145) | — | 0 moved | [] | pass |
| M3 rt143 moves / flips (124) | — | 0 / 0 | 0 | pass |
| M3 inherited bench rows identical | — | yes | yes | pass |
| M3 probes rows equal (7 files) | — | 7/7 | 7/7 | pass |
| M3 ghost answers / dup fails / write changes | — | 0 / 0 / 0 | 0 | pass |
| M3 forward n-hop moves | — | 0 | 0 | pass |
| M4 median(268b) − median(138nb) | — | −0.005 ms | <= +5 ms | pass |

\* M2 question writes: my PASSMARKS predicted [] but both arms write on
the same 4 teach_control items (a teach-as-question legitimately stores;
the sealed scorer marks all 4 right on both arms). The design note's M2
has no writes bar (0 new wrong + keep all rights); per the design marks
M2 passes. The extra prediction miss is reported here.

## Every move (panel: bug family only; dev: 46 predicted)

Panel bug ids (ids only, no text):
- right on 268b (11): n268b-001, n268b-003, n268b-005, n268b-006,
  n268b-008, n268b-009, n268b-011, n268b-012, n268b-013, n268b-015,
  n268b-016 — all with right_names and the label.
- miss, honest non-answer, stage bench73, no taught name (4): n268b-002,
  n268b-004, n268b-007, n268b-014.
- wrong (1): n268b-010, stage loop138-nhop, forward-pattern reply naming
  taught non-gold values (see diagnosis).
- 138nb on bug: 0 right, 16 wrong, all stage loop138-nhop.

Panel stage census 138nb → 268b on bug (counts only):
- 7 to loop190-reverse (right + label); 1 to loop221-table-inverse
  (right + label); 3 to loop221-table-label153 (right + label);
  4 to bench73 (miss, honest non-answer); 1 stays loop138-nhop (wrong).

Dev (46/46 exact stage+reply, 0 teach changes; categories only):
- to 190 gold + label (8): d01, d03, d29, o02, b12, b14, b19, b41.
- to bench73 "Was that a question?" (3): d02, d04, b13.
- to honest decline (4): d05, d06, o04 (190), b17 (153-reverse).
- to none abstain (13): d11, d12, o01, o20, o28, o29, b01, b15, b18,
  b22, b23, b24, b40.
- to table-inverse gold + label (8): d16, p01, p04, b04, b05, b06, b25,
  b26.
- to table-label153 true fact naming the gold subject (10): d33, d34,
  o09, o15, o18, p02, b03, b07, b09, b16.
- 315/361 other dev turns byte-identical, including all teaches, all
  forward/uncued/no-chain controls, and the forward over-walks.

## Deviations (all disclosed; no sealed file edited)

1. **Driver-only scorer bugs, fixed in a NEW file
   `scripts/claude_268b_score_fix1.py` (sealed `claude_268b_score.py`
   untouched):** (a) dev new-wrong check built mismatched dict keys
   (("d","t0") vs ("d",0)) and crashed with KeyError; (b) invpanel score
   loader assumed a bare list while the sealed scorer writes
   {"per_item": [...], ...}. Diff: 5 added lines (int-keyed map +
   ["per_item"] indexing + comment). Registered DATA used sealed
   drivers only; the fix only reads them.
2. **New post-seal runner `scripts/claude_268b_m1run.py`:** the sealed
   panel runner writes the invpanel row format (no question_stage);
   this panel's sealed scorer schema-requires question_stage (recorded
   as the panel's own run_base.py does, from loop.ears.last_stage).
   Disclosed here; panel + scorer used unchanged.
3. **M2 extra-prediction miss:** predicted question_wrote [] but both
   arms write on the 4 teach_control items (legitimate, right on both).
   Design-note M2 bars all pass.
4. **Panel folder was already committed in this worktree** (commit
   f4df2e447 by the panel writer); I extracted the same sealed content
   over it and verified `shasum -c` 5/5 OK. I never edited, read items
   of, or tuned on the panel; only category-level README + sealed
   scripts were used, and rows were run once per arm.
5. **Early smoke-test contamination (pilot only, no registered
   effect):** one inline smoke imported both arms in a single process,
   so its "138nb" lines ran with the guard's global rebind active. All
   registered/pilot numbers come from separate one-arm processes.

## Diagnosis note (the one follow-up this experiment was built for)

The guard's reverse-shape list (R1-whose, R2-married-to, R3-who-has-as,
R4-what-verb) does not cover "Who <verb>" employer/work shapes (e.g. a
"Who works at/for V?"-class question about an employer-valued V). On
n268b-010 the composer built an (employer-valued start, [employer])
frame, the guard predicate returned None, and loop138-nhop answered the
forward-walk fact naming taught non-gold values — the exact diagnosed
bug surviving, tripping falsifier P268b.6 clause 1. The 4 bench73 misses
are the predicted married-to class ("Was that a question?", no layer
parses it): honest non-answers, never wrong, but not label-bearing
rights either, so even counting them as abstains the 14/16 bar was out
of reach (11 + 4 = 15 items non-wrong, 11 right).

## What it means (plain high-school English)

- Moving the same guard onto the table-reader base fixed 15 of 16
  real bug cases: 11 now give the right person with a "worked out
  backwards" note, 4 give an honest "I can't answer that" instead of a
  wrong answer.
- Nothing else changed at all: all 44 non-bug panel questions, all
  frozen test suites, all restart checks, and running speed are exactly
  as before.

## What it doesn't mean

- It does not prove backwards questions are fixed: one bug shape still
  gets a wrong answer, and four shapes get a shrug instead of an
  answer — the 14-of-16 goal failed.
- It says nothing about any other question type: the guard only touches
  backwards-shaped questions, and the tests confirm everything else is
  byte-identical, not improved.
