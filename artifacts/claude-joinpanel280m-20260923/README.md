# joinpanel280m — blind panel (writer's README)

90 turns total. All names invented and fictional. No code was read or run to
write this panel; it was written from the panel-spec section only.

## Counts per category

| category  | turns | dialogs    | gold values                                              |
|-----------|-------|------------|----------------------------------------------------------|
| ability   | 25    | a01..a25   | "ability_list" (all 25)                                  |
| teach     | 8     | c01..c08   | stored triple Subject\|relation\|Object (all 8)           |
| called    | 12    | c01..c08   | exact expected value (all 12)                            |
| smalltalk | 25    | s01..s25   | "smalltalk" (all 25)                                     |
| mixed     | 10    | x01..x10   | "ability_list" (x01..x05, smalltalk+ability), "abstain" (x06..x10, smalltalk+untaught called question) |
| control   | 10    | k01..k05   | triple for the 5 teach turns, exact value for the 5 question turns |
| TOTAL     | 90    | 73         |                                                          |

## Structure notes

- Each called question sits in the same dialog after its teach turn
  (turn_index 0 = teach, 1..2 = questions). 8 teaches, 12 questions: four
  dialogs carry 2 questions (c01, c03, c05, c08), four carry 1.
- The 12 called questions rotate through four formal shapes: "What is N's R?",
  "What is the name of N's R?", "Who is N's R?" (person-valued only),
  "N's R is called what?".
- Controls are 5 teach+question pairs (plain wording) in dialogs k01..k05.
- Mixed x06..x10 ask about names never taught anywhere in the panel, so the
  only supportable gold is "abstain". Mixed items are owned by 260 for M1
  agreement; golds here are the writer's labels only.
- turn_index is 0-based within each dialog.
- Columns per line: dialog_id, turn_index, user_text, category, gold. No
  other keys.
