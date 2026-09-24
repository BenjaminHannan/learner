# claude-lispanel314-20260924 (sealed, test-only)

Blind conversation panel written 2026-09-24. Test use only; do not tune on it.

Files: `panel.jsonl` (user turns), `key.jsonl` (facts to save, expected answers).

## Counts
- Dialogs: 40 (7 to 10 turns each)
- Turns: 354
  - teach: 135 (40 of them state two facts)
  - correct: 10 (10 dialogs, one each)
  - ask: 129
  - smalltalk: 72
  - other (hedged / reported / hypothetical, must not be saved): 8 (8 dialogs, one each)
- Keyed facts: 185 (175 from teach turns, 10 from correct turns); 90 with owner "me", 95 about other named people, pets or places
- Asks with an answer: 109
- Asks with answer null (never told): 20, of which 8 target an "other" turn
- Names: invented, none starting with N to Z
