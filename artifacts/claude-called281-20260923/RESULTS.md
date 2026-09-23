# Exp 281 — RESULTS: FAIL (M1 stored bar 16/25; every other bar passes)

Blind panel M1 run once per arm on 2026-09-23 with the sealed agent/config
plus post-seal panel drivers (see Deviations; sealed files unchanged, own
seal re-verified 15/15 OK, panel seal OK). Panel: 60 turns / 10 dialogs,
split 25 stored_called + 10 nostore_called + 10 ambiguous_called + 10
teach_setup + 5 control_plain, exactly the brief's spec. Raw rows:
`run/panel-260.json`, `run/panel-281.json`; score: `run/panel-score281.json`,
`run/panel-score.txt`. M2/probes figures below are the registered
`run/regscore.txt` (VERDICT PASS); the panel folder was never read item by
item and no item text is quoted here.

## M1 — blind calledpanel281, 260's number next to every figure

| bar | 281 | 260 | verdict |
|---|---|---|---|
| stored ≥ 90% exact (≥ 23/25) | 16/25 | 0/25 | FAIL |
| stored wrong answers | 0 | 0 | PASS |
| notstored abstain (0 guesses) | 10/10 | 10/10 | PASS |
| ambiguous same as 260 (0 moves) | 10/10 | — | PASS |
| control same as 260 (0 moves) | 5/5 | — | PASS |
| M3 store diffs 281 vs 260 (all 60 turns) | 0 | — | PASS |
| M3 question writes on 281 | 0 | 0 | PASS |
| teach gold triple stored | 8/10 | 8/10 | identical |

Totals: stored misses on 281 are 9/9 abstains (0 wrong). Ambiguous abstain
10/10 on both arms. Control right 4/5 on both arms (the 1 miss is shared:
its dialog's teach fails on both arms). Teach misses (2) are shared: both
arms store 8/10 gold triples, per-turn stores and teach write counts
identical 10/10.

## Every move vs 260 on the panel (16 items, all toward right, 0 against)

- stored right on 281 (16): D01#1, D01#2, D01#3, D03#1, D03#2, D04#1, D04#2,
  D05#1, D05#2, D05#3, D06#1, D06#2, D07#1, D07#2, D08#2, D09#1
- stored miss on 281 (9, all abstain): D02#1, D02#2, D02#3, D03#3, D04#3,
  D08#1, D09#2, D10#1, D10#2
- 0 flips toward an abstain anywhere (no 260-right item is abstain on 281),
  so no 5× single-item follow-ups were needed. 0 wrong answers on 281.

## M2 + probes (registered `run/regscore.txt`, PASS)

- sessions152 (180 units): 0 moved. bench 4×200: 0 moved. GATE clean.
- rt136 (145 units): 0 field diffs vs 260's rows (labels vs 138j base
  identical on both arms; the NOT-clean gate string is 13 inherited 222
  WRONG-WRITE + 1 junk, equal on both arms).
- rt143_nogate (124 rows): 0 moved.
- verifier probes: exactly the predicted changed row N06 (name-of question
  with the fact stored → the head's own plain-question answer, ev 0,
  stored identical); supp 12 rows: 0 changes.

## Report-only: broken "don't know X's R called/named." abstains

- 281: 10 turns still carry the malformed abstain; 260: 21 turns. The fix
  removes it wherever it answers; remaining ones are not-stored items,
  ambiguous items, and stored items in wordings outside the four sealed
  shapes (kept byte-identical to 260 by design).

## Deviations

1. Post-seal driver addition (sealed files unchanged; own seal re-checked
   15/15 OK before the registered runs): the writer's schema is per-turn
   rows `{dialog_id, turn_index, user_text, category, gold}`, while the
   sealed `claude_281_panel.sh` + `claude_called281_run.py` load
   whole-dialog items. New files `scripts/claude_called281_panelrun.py`
   (dialog-wise runner, fresh daemon per dialog), 
...[truncated 1474 chars]