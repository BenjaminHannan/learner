# Same-claim judge (lis-319c-full). Fixed 2026-09-26 before any pair existed.

Never use WebFetch. Never call any mcp__hearthbot__ tool. Do not run git. Do not open any file except your input.
Input: PAIRS.jsonl, one pair per line: {"pid","id","prev_reply","turn","saved":{"owner","rel","value","mode"},"gold":{"owner","relation","value"}}.
"saved" is what a reader wrote to a notebook after reading the user's "turn" (prev_reply = the assistant's reply just before).
"gold" is what a labeller says the turn states. Owner "me"/"user" = the person typing.
For each pair answer same = true only if the saved fact states the same claim as the gold fact:
- the same person (a first name is the same person only if the turn leaves no doubt who it is),
- a relation with the same meaning (e.g. employer ~ "works at"; city ~ "lives in"; NOT employer vs school, NOT
  place_of_birth vs city, NOT friend vs sister; a narrower saved relation is same only if the turn states the narrower one),
- the same value.
Otherwise same = false. Judge each pair on its own; do not guess what the labeller meant beyond the turn.
Output: one JSON line per pair {"pid": int, "same": true|false}, every pid exactly once (check with Python).
Reply with counts only (true, false). Never quote any text from the file.
