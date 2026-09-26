k1fpanel (TEST-ONLY, blind). Counts only. Do not quote, train on, or tune on these items.

- File: items.jsonl, 100 lines, one JSON object per line, ids kf-001 .. kf-100.
- Fields per line (8): item_id, kind, turns, last, facts, numbers, target, gold_expr.
  numbers, target and gold_expr are always null.
- Kinds: idea = 70, uses_facts = 30.
- idea with 1 lead-in turn: 35; idea with 0 lead-in turns: 35. idea facts are always empty.
- uses_facts teach turns: 1 turn = 10, 2 turns = 10, 3 turns = 10. uses_facts facts are always non-empty.
