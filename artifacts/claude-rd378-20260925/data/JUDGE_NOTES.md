# Note judge brief (reading thread, rd-378)

Never use WebFetch. Never call any mcp__hearthbot__ tool. Do not run git. Never read any "panel" folder or
/mnt/project-files/escrow-331. Do not open any other notes_w*.jsonl than your input, and not the writers' source folders.

Input {INPUT}: one dialog per line: {"dialog","kind","speakers","date","turns":[{"t","speaker","text","notes":[{"text","cites","when"}]}]}.
cites are offsets from the note's own turn (0 = that turn, -1 = the turn before, ...).

For EVERY note, read the dialog up to and including the note's turn and give one verdict:
- ok: one plain sentence, third person with names (or "the user"), and everything in it is stated by the cited turns
  (reading the earlier turns only to know who "she"/"that" is); plans stay plans, claims about others stay claims.
- unsupported: it says something the cited turns do not state (a guess, an inference, a wrong detail, wrong person).
- bad_cite: true to the dialog but a turn it needs is not cited, or a cited turn is not needed.
- bad_when: "when" is wrong (not the time the turns give for this note, or missing when the turn gives one).
- bad_form: pronoun instead of a name, first/second person, more than one sentence, a joke or hypothetical turned into a fact.
For EVERY non-assistant turn, also say "missed": the number of clearly memorable things in that turn (an event, plan,
preference, change, time, person or pet fact) that no note of that turn covers (0 if none).

Output {OUTPUT}: one JSON line per non-assistant turn: {"dialog", "t", "verdicts": [one per note, in order], "missed": int}.
Check with Python that every non-assistant turn of the input has exactly one line and verdict counts match note counts.
Reply with counts only (verdict totals, turns with missed > 0). Never quote dialog text.
