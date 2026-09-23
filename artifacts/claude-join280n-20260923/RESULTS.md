# Exp 280n — RESULTS (registered re-test of the SEALED 280m agent, no code change, CPU only)

## Result first

**Registered verdict: FAIL on the M1 bar only: agreement 87/90, bar 90/90.**
M2 PASS (exactly the predicted union, gates identical to 260's).
M3 PASS (wellbeing 17/20 vs 260's 16/20, every other item identical, 0 writes/diffs).
M4 PASS (0 store diffs on the panel; 0 write changes on the suites).
Seals after the runs: own 3/3 OK, 280m 12/12 OK, panel 2/2 OK. No sealed file changed. No re-seal. No silent re-runs.
(Categories and counts only below; no panel item is quoted.)

## Marks table (integer counts)

### M1 — blind joinpanel280n, once per arm (73 dialogs, 90 turns)

| category | turns | 280m agree with owner | owner |
|---|---|---|---|
| ability | 25 | 25 | 280b |
| teach | 8 | 8 | 260 |
| called | 12 | 12 | 281 |
| smalltalk | 25 | 25 | 282b |
| mixed | 10 | 10 | mechanical (280b: 5, 260: 5) |
| control | 10 | 7 | 260 (fixed) |
| **total** | **90** | **87** | bar 90/90: **FAIL** |

| check | count | bar | result |
|---|---|---|---|
| overlaps (mixed turns with 2+ piece arms differing from 260) | 0 | 0 | pass |
| 280m writes on question turns | 0 | 0 | pass |
| 280m writes on smalltalk turns | 0 | 0 | pass |
| store diffs 280m vs 260 | 0 | 0 | pass |
| old-sheet scan hits on 280m replies | 0 | 0 (director claim check) | pass |
| wrong called answers on 280m | 0 scored here | 0 (director claim check) | pass (files listed below) |

Report-only rates (CAN-line replies, 280m beside 260): ability 19 vs 11; mixed 5 vs 3;
teach 0 vs 0; called 0 vs 0; smalltalk 0 vs 0; control 0 vs 0.

### Every move (all 3 misses, ids only)

- `ct00#1` (control -> 260), `ct01#1` (control -> 260), `ct04#1` (control -> 260).
- All 3 are turn 1 of 2-turn dialogs. On each miss, measured mechanically from the recorded rows:
  only 281's reply differs from 260's (260 == 280b == 282b, 281 differs), and 280m is byte-identical to 281
  (reply lengths 24/23/24 vs 260's 36/43/34). Write counts 0 on all arms. Stored triples identical on all
  arms (the turn-0 teach triple is preserved). No CAN-line text on any arm on these turns.
- So every one of the 90 turns equals some piece arm (87 owner-agree + 3 where 280m == 281). No turn has 2+
  piece arms differing from 260. No new behaviour beyond the pieces.

### M2 — frozen suites + verifier probes vs 260's rows (registered after-seal run): PASS

- sessions152: exactly 3 reply-only moves (S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9),
  reply-only move = 3, write change = 0. Matches P280n.2 exactly.
- bench 4x200: 0 moved.
- sessions152/bench gate: clean, identical to 260's.
- rt136: 145 rows, 0 field diffs; gate identical to 260's (NOT clean on both arms, same inherited counts).
  vs-138j-base labels identical to 260's.
- rt143_nogate: 124 rows, 0 diffs.
- verifier probes: vp diffs exactly [N06, E04] (N06 reply and store match the predicted values), supp 0 diffs.
- Regscore verdict line: PASS.

### M3 — smalltalkpanel234, once on 260 and once on 280m: PASS

- n = 56. Wellbeing: 260 16/20, 280m 17/20 (miss ids on 280m: s234-015, s234-016, s234-020).
  Every other item: 36/36 identical. 280m writes: 0. Store diffs: 0. Setup diffs: 0.
- The 1 wellbeing move is the same row 282 moved (inherited, as on 280m).

### M4 — notebook-zero: PASS

- Panel: 0 store diffs 280m vs 260. Suites: 0 write changes, 0 store diffs per the regscore row compare.

## Predictions resolution

- P280n.1: figure wrong (87, not 100); right on 0 overlaps, 0 question/smalltalk writes, and the old-sheet
  scan (0 hits). The mixed-turn fix worked: mixed 10/10 under the mechanical rule (owners 280b: 5, 260: 5),
  including the ability-led shape that missed on 280m. The 3 misses are a new instance of the same defect
  class: the fixed control -> 260 rule did not predict that a control turn could carry called wording that
  fires only the 281 rewrite (only 281 differs from 260 there, and the join correctly routes 281-inner first).
- P280n.2: right, exactly (3 sessions152 moves, 0 elsewhere, vp N06+E04, vs 0, gates identical).
- P280n.3: right (17/20 vs 16/20, 36/36, 0 writes/diffs).
- P280n.4: the bar-miss clause tripped on the 3 control turns (280m differs from fixed owner 260); no
  suite/probe falsifier and no overlap tripped.

## Deviations

- None from the registered protocol. The panel sealed ~4 minutes after this seal (within the 120-minute
  window); panel seal checked 2/2 OK before the single run. Each command ran once. The sealed M2 runner
  waited on machine load internally (1-min load above 60) before starting steps; total M2 time 518 s.
  No sealed script broke; no driver fix was needed.
- Protocol note: the task's PUSH line asks for commits/pushes, but the standing rules forbid git commits, PRs
  and pushes, so no commit or push was performed. The files listed below are in place in the worktree for the
  director to collect. The ledger was appended (P280n.1–P280n.4); no existing ledger line was changed.

## Reply files for the director's claim check

- `artifacts/claude-join280n-20260923/run/panel-280m.json` (all 280m replies, per-turn write counts, stores)
- `artifacts/claude-join280n-20260923/run/panel-260.json`, `panel-280b.json`, `panel-281.json`,
  `panel-282b.json` (the four reference arms)
- `artifacts/claude-join280n-20260923/run/probes-280m.json` (canonical probes on 280m)
- `artifacts/claude-join280n-20260923/run/panel-score280n.json` (agreement rows, old-sheet scan, miss ids)
- Called answers (10 right, 2 clarify lines, 0 wrong on 280m) and the ability-text check (only CAN280 text,
  0 other claims) are director-graded from these files.

## What it means (plain high-school English)

- The join itself behaved exactly as built on all 90 fresh turns: every reply came from one of its parts,
  nothing was written except on teaching turns, and nothing was memorized differently from the base.
- The new counting rule fixed last time's problem: all 10 mixed turns now match their rightful owner.
- What failed is again the prediction about who owns a turn, this time on 3 control turns that use called
  wording: the plan said those belong to the base, but the join (correctly, by its construction) lets the
  called-question part answer them.

## What it doesn't mean

- It doesn't mean the join learned anything new or broke anything old: the frozen school tests match the base
  everywhere except the 5 pre-approved moves, and small talk got slightly better, never worse.
- It doesn't mean mixed turns overlap: zero turns had two parts fighting over them.
- It doesn't change the 280m verdict or any sealed file: all seals still check out.
