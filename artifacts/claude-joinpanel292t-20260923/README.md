# joinpanel292t — blind panel (re-test of the talking-line join)

Built blind from the joinpanel280m spec only. No code read, no code run,
no other panel or artifacts folder opened. All names freshly invented.

## Counts per category (90 turns total, 78 dialogs)

| category  | turns | dialogs                              |
|-----------|-------|--------------------------------------|
| ability   | 25    | ab_01..ab_25 (1 turn each)           |
| teach     | 8     | turn 0 of tc_01..tc_08               |
| called    | 12    | tc_01..tc_04 x1, tc_05..tc_08 x2     |
| smalltalk | 25    | st_01..st_25 (1 turn each)           |
| mixed     | 10    | mx_01..mx_10 (1 turn each)           |
| control   | 10    | cx_t_01..cx_t_05, cx_q_01..cx_q_05   |

## Gold conventions

- ability -> "ability_list"; smalltalk -> "smalltalk".
- teach (incl. control teaches) -> stored triple Subject|relation|Object.
- called -> exact expected value.
- control questions ask about never-taught names -> "abstain"
  (no-hallucination controls; plain "What is X's Y?" shape).
- mixed -> piece answer (see PASSMARKS below), never "abstain".

## The four formal called shapes (3 uses each across the 12 called turns)

A. What is <Name>'s <relation> called?
B. What is <Name>'s <relation> named?
C. What do they call <Name>'s <relation>?
D. Name <Name>'s <relation>.

Mixed-called turns use casual variants outside these four shapes so the
formal-shape count stays exactly 12.

## PASSMARKS — predicted piece route for each mixed turn (pre-seal)

- mx_01..mx_05 -> ability piece (gold "ability_list").
- mx_06 -> called piece, teaches resolve via tc_01 (gold "Miso").
- mx_07 -> called piece, teaches resolve via tc_02 (gold "Halcyon").
- mx_08 -> called piece, teaches resolve via tc_03 (gold "Crumbline").
- mx_09 -> called piece, teaches resolve via tc_04 (gold "Beaker").
- mx_10 -> called piece, teaches resolve via tc_05 (gold "Foxglove").

Note: mixed-called turns reference subjects taught in tc_01..tc_05.
If dialogs are scored in strict isolation (fresh state per dialog),
mx_06..mx_10 have no in-dialog teach and would read as abstain cases;
the golds above assume panel-order state (teaches persist).

## Columns

Exactly: dialog_id, turn_index, user_text, category, gold.
turn_index starts at 0 within each dialog; every called question sits
after its teach in the same dialog.
