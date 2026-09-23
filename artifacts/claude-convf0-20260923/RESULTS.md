# convbench-f0 baseline on base 292 (step F0)

Result: 286 turns run once on 292; mechanical counts only, no grader.

## Counts

- turns: 286
- benchmark lines: 286 (teach 84, ask 84, smalltalk 68, correct 10, other 40)
- run rows: 286; join misses vs benchmark: 0
- clarify / not-understood replies: 197 (68.9%)
- clarify marker strings used (exact, lowercase substring match):
  - "didn't understand"
  - "don't know that shape"
  - "well enough to save"
  - "don't know that yet"
  - "do not know that from what you taught me"
  - "couldn't save that as a fact"
  - "couldn't read that message"
  - "please say it like"
  - "do not understand that question"
- most common reply count: 122 (42.7%)
- most common reply text: 'I couldn\'t save that as a fact. I don\'t know that shape yet. Could you say it another way, like "Kim\'s boss is Lee."'
- distinct replies: 77
- mean reply length: 17.49 words
- replies starting with "Saved:": 20
- replies starting with "Updated:": 0
- ask turns: total 84; right 6; wrong 1; abstain 77
- teach turns: total 84; saves matching gold 13; non-matching 71

## Rules

- Clarify = reply contains any listed marker (case-insensitive).
- Ask abstain = clarify or extra abstain markers ("don't know", "do not know", "haven't told me", "no record", "will not guess", "won't guess").
- Ask right = not abstain and gold value (exact, case-sensitive) is a substring of the reply; else wrong.
- Teach save-match = gold "Subject|relation|Object" appears exactly in stored_triples after the turn.
- Benchmark user turns are never quoted in this file.
