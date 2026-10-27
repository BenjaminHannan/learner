# lis-320 addendum 1: ask-back rows (a mark added before the panel is sealed and before any read or training)

Written 2026-09-26 17:11 UTC. Source: Trustworthy notes' lead 44c4b4341. In 0.2c the build asked "is Kim's occupation marine
biology?", the user answered "ok ty, gonna sleep on it. night!", and the fact was saved. The reader took the assistant's own
question as the user's words, which is a source-monitoring error. The Thread manager asked for this at 17:04.

## Data (not a second change: part of lis-320's one change, the training rows)
The seeder gets two new intents, used in the full run with --ask-back (the 30-call pilot ran without them, with the same
seeds as before):
- ack_after_ask: the assistant asks a yes/no question checking a detail the user has not given, and the user only
  acknowledges. Gold: no fact.
- yes_after_ask: the same question, and the user answers yes. Gold: the fact, with owner and value taken from the question
  (the compiler already accepts a value from a prev_reply that ends in "?").
The code checks require that the question names the value (and the person, or "you"), ends in "?", and that an ack turn
has no yes/no word while a yes turn has a yes, no no, and no hedge. Scripts: claude_lis320_seed.py, claude_lis320_glm.py
and claude_lis320_check.py (selftests pass).

## Panel
The readpanel320 writer was told, while writing, to add at least 15 ack_after_ask rows (lookalike, no fact) and at least
10 yes_after_ask rows (fact value verbatim from prev_reply). The blind labeller's rules gained the matching general rule.

## Mark
| Mark | Bar |
|---|---|
| R7 | new ack_saves = 0 (saves on ack_after_ask rows; scripts/claude_lis320_score.py extra) |
PASS now needs R1 to R7. Validity also needs 12 or more ack_after_ask rows. yes_saved_right is reported for both readers,
with no bar.
