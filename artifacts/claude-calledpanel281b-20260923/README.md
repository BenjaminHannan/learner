# calledpanel281b (blind panel for exp 281b) — README

60 turns total, one JSON object per line in panel.jsonl with exactly the keys
dialog_id, turn_index, user_text, category, gold.

Counts per category:

- teach_setup: 10 (plain form "<Name>'s <relation> is <Value>.", dialogs d01-d10,
  turn_index 0; gold is the stored triple Subject|relation|Object)
- stored_called: 25 (called/named/name-of questions, each after its teach in the
  same dialog; 14 typed casually: all-lowercase, no apostrophe, no question mark,
  "whats"/"what is"; gold is the exact expected value)
- nostore_called: 10 (same shapes about names never taught, dialogs d11-d15;
  gold "abstain")
- ambiguous_called: 10 ("called belongs to the name" items about works titled
  with the word after called, dialogs d16-d20; gold "abstain")
- control_plain: 5 (plain-form questions about taught facts, last turn of
  dialogs d01-d05; gold is the exact expected value)

All names and titles are invented for this panel. No item quotes any other panel.
