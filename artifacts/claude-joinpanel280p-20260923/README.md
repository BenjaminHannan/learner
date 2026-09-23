# joinpanel280p — blind panel (re-test of the talking-line join)

Blind panel writer. No code read or run. Fictional names only, freshly invented.
One line per turn in panel.jsonl with exactly these keys:
dialog_id, turn_index, user_text, category, gold.

## Counts per category (turns, total 90)

- ability: 25
- teach: 8
- called: 12
- smalltalk: 25
- mixed: 10
- control: 10
- total: 90

## Dialog layout

- ability: 25 dialogs (ab_01..ab_25), turn 0 only. Gold "ability_list".
- smalltalk: 25 dialogs (sm_01..sm_25), turn 0 only. Gold "smalltalk".
- teach+called: 8 dialogs (tc_01..tc_08). Each opens with one plain teach
  "<Name>'s <relation> is <Value>." at turn 0 (category teach,
  gold Subject|relation|Object). Called questions follow in the same dialog:
  tc_01..tc_04 have 2 called each (turns 1-2), tc_05..tc_08 have 1 called
  each (turn 1). 12 called total. Four formal called/named shapes rotated,
  each used 3 times:
  S1 "What is <Name>'s <relation> called?",
  S2 "What is <Name>'s <relation> named?",
  S3 "What is the name of <Name>'s <relation>?",
  S4 "Tell me the name of <Name>'s <relation>?".
  Gold for called is the exact taught value.
- mixed: 10 dialogs (mx_01..mx_10), turn 0 only. Each mixes casual small talk
  with an ability question. Gold "ability_list".
- control: 5 dialogs (ct_01..ct_05) x 2 turns = 10 turns. Turn 0 is a plain
  teach (category control, gold Subject|relation|Object); turn 1 is a plain
  question "What is <Name>'s <relation>?" (category control, gold exact value).

## Notes

- Chat-style typing throughout. All names/values fictional.
- No abstain items used.
- Sealed with shasum -a 256 over panel.jsonl and SPEC-COPY.md.
