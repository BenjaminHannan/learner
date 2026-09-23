# Merge 138p: RESULTS

**Result: FAIL on M7 (two blind panels). M1–M6 all PASS on the first
try.** No re-runs, no changes after the seal (re-verified 9/9 OK).
Registered run took 900 s for M1–M6 plus the M7 panels once each
(load-gated throughout; free disk stayed above 3 GB).

138p = 138m + 260 (openers) + 252c (corrections), built in
`scripts/claude_loop138p_agent.py` (layer order and overlap analysis in
`design/v3/30-modes/138p-merge-muse.md`). Ledger predictions P138p.1–.5;
this file reports the outcomes. P138p.1–.3 and P138p.5's M1–M6 parts were
right; P138p.4's count-level panel predictions were wrong on two panels
(details below); P138p.5's overall PASS prediction was wrong.

## Marks

| Mark | What | Bar | Result |
|---|---|---|---|
| M1 | 138m L1 sets, 990 cases (own/head/138m/138p) | own reproduces sealed rows; 0 unpredicted/wrong/missing vs head | 990/990 sealed rows; 209/209 predicted moves exact; 0/0/0. **PASS** |
| M1 | 260 devcases, 109 | own reproduces 260 rows; 138p == own | 109/109; 109/109 identical; 138m 45/109. **PASS** |
| M1 | dev252b 56 / dev258 79 / dev259 66 | 252c re-run == registered rows; 138p == 252c except predicted ids | 201/201 fidelity; dev252b 0 diffs; dev258/259 exactly the 14 predicted abstain-wording ids; 0 false replies; junk only d258-037, v259-008 (known). **PASS** |
| M2 | Frozen suites vs 138m rows | move sets = predicted; justified ids only; 0 flips | sessions152 1, bench 0, marks123 2, rt136 labels 20 (13 inherited + C122 + 6 reply-only), direct moved 5, rt143 0 moved / 0 flips. **PASS** |
| M3 | Sleep smoke | only agent/config/label/seconds differ | exactly those 4. **PASS** |
| M4 | Bench ×3 | 4/4 files byte-identical | 4/4. **PASS** |
| M5 | Latency | median(138p)−median(138m) ≤ +5 ms | 2.173 vs 2.062 ms, +0.111 ms (624 turns each). **PASS** |
| M6 | Restart + verifier dialogs | 0 ghosts/dup-fails/bad writes; changes = predicted; probes == 260 rows | 2/2 predicted asks; 0/0/0; vp/vs byte-identical to 260; m == base. **PASS** |
| M7 | openpanel260 (80, arms 260/138m/138p once each) | fidelity 100%; bars vs 260 | fidelity 80/80 rows + identical re-score; 138p 80/80 (260 80/80, 138m 38/80); 0 right→wrong; 0 junk; 0 question writes; control 16/16 identical. **PASS** |
| M7 | corrtail258 (80, arms 252c/138p once each) | fidelity 100%; no right→wrong; bars | fidelity 80/80 rows + identical re-score; 138p 53 vs 252c 54; right→wrong 1 (t258-049); keep 7/8 identical. **FAIL** |
| M7 | corrpanel252 (100, arms 252c/138p once each) | fidelity 100%; only c252-022 moves | fidelity 100/100 rows + identical re-score; 138p moves 10 (c252-022 correct + 9 extra); M4_pass false. **FAIL** |

## Every move

### M1-A: 209 moves vs line head (all predicted exactly; run/l1-judge.json)

- 219: 0 moves.
- 230: 52 (same ids as 138m; all 52 records identical to 138m's).
- 230c: 1 (e03, identical to 138m's).
- 227: 12; 227b: 12; 227c: 61 (all records identical to 138m's).
- 224c: 32 (identical to 138m's).
- 233: 13 (12 identical to 138m's + D52 "Brisa doesn't live in Tolmark."
  → "OK, I removed Tolmark as Brisa's city.", 252 rule-1 denial).
- 234: 26 (21 identical to 138m's + D059/D062/D068 greeting→answer/greet
  per 260 + new D063 "Hi there, what is my name?" → "I don't know your
  name yet." per 260).

### M1-B/C devs

- 260 dev: 138p == 260 on 109/109 (0 moves).
- dev252b: 138p == 252c on 56/56 (0 moves).
- dev258: 7 diffs (d258-044, 046, 051, 054, 056, 060, 075-extra):
  long-decline → Q2 (6) or save-failure (044); stores identical.
- dev259: 7 diffs (v259-040, 041, 043, 053, 054, 056, 059):
  long-decline (043: "I cannot predict.") → Q2 or save-failure (053);
  stores identical.

### M2 (run/sd, run/sd136, run/rt143nogate-p.json)

- sessions152 (1): S3-teachers-correction#6 reply-only (252 inferred-ask;
  UNHELPFUL→UNHELPFUL, stores identical).
- bench: 0. marks123 (2): B_corrections-04 (252 pronoun correction,
  byte-identical on 252c; rt81 UNCLEAR→BUG is the harness's FakeEars
  expectation), -05 (follow-on "I already have that.").
- rt136 labels (20): C019–C031 inherited 222 WRONG-WRITE (rows identical
  to 138m's except seconds, 13/13) + C122 (260 exemption, exact record)
  + reply-only C071/C072/C073/C075 (252 unknown-ask, OK→OK) + C076/C079
  (138m's own). Direct vs 138m moved: C071, C072, C073, C075, C122.
  0 other new WRONG / WRONG-WRITE / junk / lost-OK.
- rt143 no-gate: 0 moved rows, 0 verdict flips (124/124).

### M6 (run/probe, run/vp-p.json, run/vs-p.json)

- Restart: p3-dialogs:d08:t01 ("No, it's Aldgate.") and d08:t04 ("No
  wait, it's Pom.") → "Which fact should I change? Please say it like
  \"Kim's boss is Lee.\"" (252 no-one-fact-context ask). 0 ghosts (neither
  asserts a triple), 0 failed duplicate checks, 0 bad writes (events and
  end stores equal 138m's on all 36 dialogs; audits present 17+6+3+51+9).
- Verifier: 138p rows byte-identical to 260's registered vp-n.json (98)
  and vs-n.json (12): exactly B15:t0, B15:t1, D08:t1, D10:t0, D10:t1,
  E06:t0, E10:t0 (1 new write B15:t0; stored changes B15, D10); supp 0.
  m arm reproduces rows-138m.json / supp-rows-138m.json.

### M7 (run/m7, run/m7-check.json; scorer outputs from the SAME sealed scorers)

- openpanel260: 260 right 80/80, 138p right 80/80, 138m right 38/80.
  Moves vs 138m: 42 (the registered 260 set). 0 right→wrong vs 260.
- corrtail258: 252c right 54, 138p right 53.
  138p-vs-252c row diffs (6, all stores-identical abstain-wording swaps):
  t258-049 keep (long-decline → save-failure; right→wrong; keep 7/8),
  t258-053/054/056/057/058 question_tail (long-decline → Q2; still right).
  False claims 0/0, junk 0/0, question writes 0. t258-026 wrong value
  inherited from 252c (predicted).
- corrpanel252: c252-022 correct (class "both", "OK, I removed Tobin as
  Quenby's manager.", 1 triple removed, stores stable at followup).
  9 extra class-"neither" moves, all reply-only long-decline → Q2 with
  stores identical: c252-006/009/010/011/014/033 (followup), c252-081/
  084/087 (turn). New wrong values 0, new junk 0, false replies 0.

## Misses (10 panel rows + 2 driver/scorer bugs, all reported)

1. t258-049 (corrtail258, keep): right on 252c (and 252b/258/259), wrong
   on 138p. Only the turn reply differs (long-decline → save-failure);
   stores identical. Breaks "keep byte-identical" and "no right→wrong".
2–10. c252-006/009/010/011/014/033/081/084/087 (corrpanel252): reply-only
   long-decline → Q2 swaps (stores identical) that match neither
   registered arm byte-for-byte, so the sealed m4 rule fails them
   although nothing is newly wrong, junk, or false.
11. Sealed `claude_138p_panel.sh` references `$R2B` (defined as `$R252B`):
    the script stopped AFTER all six one-time panel runs finished but
    before the two m4 scores and the m7 tally. The sealed file was NOT
    edited (would-be diff: `R2B` → `R252B` on two lines); the two m4
    scorer commands were run once each manually with the intended path,
    and no panel arm was re-run.
12. Sealed `claude_138p_score.py` m7() crashes on the openpanel totals
    line (`dict_values` subscript) and on the tail question-write check
    (rows carry no `turn` field). The sealed file was NOT edited; the
    identical tally (plus reading turn text from the panel items file
    for the mechanical question-write check only) was run once as a
    one-off. Seal re-verified 9/9 OK afterwards.

## Deviations

1. Phase-1 analysis missed a case: on turns no layer claims, where the
   138k base returns the exact glued long decline, 138p's 224 stack
   rewords it (Q2 on questions, 138m's save-failure on statements)
   while 252c keeps it verbatim. The 14 dev rows with this shape were
   predicted (M1C); the 15 blind-panel rows with this shape (6 tail +
   9 panel) were predicted as no-move and moved. Same mechanism, same
   harmless class (honest abstain for honest abstain, stores identical)
   — but two panel bars demand byte-identity, so they fail mechanically.
2. `python3` was never used; every command ran under the uv prefix.
3. The m7 tally's question-write check reads turn texts from the panel
   items file mechanically (question-mark + store-change only); no item
   was read, tuned on, or quoted beyond ids and reply classes.
4. rt136 labels come from 138j's sealed rows (as 138m did); every row is
   also compared directly with 138m's saved rows.

## What it means (plain high-school English)

The merge works: 138p keeps everything 138m does (990/990 dev cases,
all frozen suites as predicted), everything 260 does (109/109 opener
cases, 80/80 blind opener panel), and everything 252c does (all 201
correction dev cases; the one real blind correction, c252-022, works).
It is deterministic (bench identical 3 times), fast (+0.11 ms), never
writes from a question, never stores an inferred fact, and never removes
a fact the user didn't deny. The 10 failing panel rows are all the same
harmless thing: where the old base said "I do not know that from what
you taught me…" 138p says "I didn't understand that question…" — a
different honest "I don't know", with the notebook identical.

## What it doesn't mean

- It does not mean the merge is accepted: two registered panel bars
  failed (one right→wrong keep row; nine byte-identity rule misses), so
  the verdict is FAIL and a director decision is needed on whether the
  abstain-rewording class should be exempted or fixed.
- It does not mean anything is newly unsafe: 0 new wrong values, 0 new
  junk writes, 0 new false claims and 0 question writes on all three
  blind panels.
- It does not mean the panels measure real users: 80 + 80 + 100
  scripted items, each run once.
- The two driver/scorer bugs (11, 12) were worked around without
  touching sealed files; the workarounds are logged in run/m7-check.txt
  and re-checkable from the saved rows.
