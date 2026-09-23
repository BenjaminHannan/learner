# joinpanel280n (blind panel for 280n re-test of the talking-line join)

90 turns, 73 dialogs. All names are fictional and freshly invented for this panel.
Schema per line of panel.jsonl, exactly these keys: dialog_id, turn_index, user_text, category, gold.

## Counts per category (turns)

- ability: 25
- teach: 8
- called: 12
- smalltalk: 25
- mixed: 10
- control: 10
- TOTAL: 90

## Layout

- ability: 25 single-turn dialogs (ab00-ab24). General "what can you do" questions in
  many casual wordings. Gold is "ability_list".
- teach + called: 8 dialogs (tc00-tc07). Each dialog opens with one plain teach turn
  (turn_index 0, category teach, gold is the stored triple Subject|relation|Object),
  followed by its called/named question(s). Four dialogs carry 2 questions, four carry
  1 question, for 12 called turns total. The 12 called questions use four formal shapes,
  3 turns each. Gold on called turns is the exact expected value.
- smalltalk: 25 single-turn dialogs (st00-st24). Greetings, thanks and closings typed
  casually. Gold is "smalltalk".
- mixed: 10 single-turn dialogs (mx00-mx09). Each turn mixes small talk with a question:
  6 mix small talk with an ability question (gold "ability_list"); 4 mix small talk with
  a called/named question about a person never taught anywhere in the panel (gold
  "abstain" — there is no fact to answer with).
- control: 5 two-turn dialogs (ct00-ct04), 10 turns total. Turn 0 is a plain teach
  (gold is the stored triple Subject|relation|Object); turn 1 is a plain called-style
  question about that teach (gold is the exact expected value).

## Gold conventions

- ability items: "ability_list"
- smalltalk: "smalltalk"
- called and control questions: the exact expected value
- teach turns (including control teach turns): the stored triple Subject|relation|Object
- unanswerable questions (mixed called items with no teach): "abstain"
