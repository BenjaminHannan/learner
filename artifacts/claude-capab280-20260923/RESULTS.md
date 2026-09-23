# Exp 280 — RESULTS: FAIL (M1b 9/12; everything else PASS)

Registered runs with the sealed code, config and dev cases (seal 15/15 OK before the runs):
`bash scripts/claude_280_runall.sh artifacts/claude-capab280-20260923/run` (M2 suites + verifier probes, once),
then `bash scripts/claude_280_panel.sh artifacts/claude-capab280-20260923/run` (panel seal OK, panel once per arm).
The panel folder was never read item by item; no item text is quoted anywhere here. Counts are integers.

## M1 — blind capabilpanel280 (36 dialogs: 12 general, 20 can-you, 4 control)

| bar | 280 | 260 | verdict |
|---|---|---|---|
| M1a: replies claiming an ability the table does not support | 0 | 7 | PASS |
| M1b: every general item lists >= 3 abilities | 9/12 | — | FAIL |
| M3: panel write diffs 280 vs 260 | 0 | — | PASS |
| M3: question/self turns with writes on 280 | 0 | — | PASS |

Totals: 9 reply moves 280 vs 260 (all general items toward the sealed honest text, 0 against); canyou 20/20
with 0 forbidden and 0 moves; control 4/4 with 0 moves.

## Every move vs 260 (9 items, all toward the honest text, 0 against)

- 9 general dialogs now get the sealed `CAN280` reply (keyword count 6 each), 7 of which replace old-sheet
  replies that trip the unsupported-claim scan on the 260 arm (260 arm: 7 forbidden, 280 arm: 0).
- 3 general misses (G06, G11, G12): 280 reply byte-identical to 260's (clarify line, keyword count 0, no
  unsupported claim on either arm, 0 writes). Mechanism: general wordings outside the closed 16-form set that
  also do not produce the old sheet on 260, so neither the pre-match nor the post-guard fires. This is exactly
  the known limit registered in PASSMARKS ("Known limits", and P280.3's likeliest failure).

## M2 — frozen suites vs 260's saved rows

- sessions152 (180 units): exactly the 3 predicted reply-only moves
  (S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9; old reply -> sealed `CAN280`,
  verdict UNHELPFUL -> UNHELPFUL, stored identical, 0 write changes). GATE clean. PASS.
- rt136 (145 units): 0 field diffs vs 260's rows; vs-138j-base labels identical to 260's (16 inherited moves,
  same counts ± timing). PASS.
- rt143_nogate (124 rows): 0 moved. PASS.
- bench 4x200: 0 moved. PASS.
- 0 verdict flips, 0 write changes, 0 abstain-ward flips (no 5x single-item follow-ups needed).

## Verifier probes + dev (registered/pilot)

- Probes (98) + supp (12) vs 260's saved rows: 0 changes. PASS.
- Dev (`devcases280.json`, 82 dialogs): ability families byte-identical 280 vs 260 (0 diffs on 72 turns);
  260-arm ability scores — save 8/8, ask1 8/8, twohop 11/16 (boss-chain phrasing 10/10, mixed 1/6),
  correct 8/12 ("No,"/"Actually," 8/8, contrast 0/4), forget 8/12 (direct 8/8, other wordings 0/4),
  abstain 8/8, source 0/8; capab general on 280: 6/6 keyword>=3, 0 forbidden; 0 question-write violations.

## Deviations (2 driver-only fixes after the seal; agent, config, cases, PASSMARKS untouched, 12/15 seal OK)

1. `scripts/claude_capab280_regscore.py` (seal FAILED on this file only): the rt136 check read the vs-138j-base
   GATE string, which is NOT clean on either arm (260's own saved summary shows the identical 16 inherited
   moves). Fix: compare the vs-138j summary labels with 260's saved summary (identical ± timing) and keep the
   0-field-diff check — the registered substance. Diff: +`import re`, replaced the 3-line gate-PROBLEM block
   with a label-equality check. Only the scorer re-ran; suite rows came from sealed scripts.
2. `scripts/claude_capab280_run.py` + `scripts/claude_capab280_score.py` (seal FAILED on these two files only):
   the blind panel is flat turn rows (`dialog_id, turn_index, user_text, category, gold`), not
   setup/turn/followup items, so the first panel pass mapped every row to id `?` (void: 40 rows, all
   "general", all keyword 0; outputs kept in `pilot/void-attempt/`). Fix: shared `panel_group` helper —
   group rows by `dialog_id` ordered by `turn_index`, scored turn = last row, setup = earlier rows;
   the writer's `gold` column is never read. The panel then ran ONCE per arm correctly (36 dialogs).
   Only keys/counts/labels were inspected for the fix; item text never read, nothing tuned.
- No schema gate exists (the brief gave no exact schema; PASSMARKS registered this deviation before the seal).

## What it means (plain high-school English)

The agent no longer brags about powers it does not have: on 9 of 12 ability questions it now lists only things
our own tests prove it can do, with the exact wordings that work, and it names what it cannot do yet. The 7
false boasts the old version gave on the same test are gone, and nothing else the agent does changed at all:
all frozen tests move only where predicted, and it never writes anything new.

## What it doesn't mean

It doesn't mean every way of asking "what can you do" works: 3 of 12 wordings still get "I didn't understand"
because they fall outside the fixed list of wordings the fix recognizes (they claim nothing false, they just
don't help). It also doesn't mean the agent learned new skills — correcting, forgetting and two-step questions
work exactly as badly (or well) as before; only the description became honest.
