k1apanel (TEST-ONLY, blind). Counts only. Do not quote, train on, or tune on these items.

File: items.jsonl (JSON Lines), 60 items, ids kc-01 .. kc-60, kinds shuffled through the ids.

Counts:
- kind "idea": 40
  - with 1 lead-in turn: 20
  - with 0 lead-in turns: 20
  - facts: [] on all 40
- kind "uses_facts": 20
  - with 1 teach turn: 6
  - with 2 teach turns: 8
  - with 3 teach turns: 6
  - total fact entries: 76 (each {"owner", "relation", "value"})

Fields per line (8): item_id, kind, turns, last, facts, numbers, target, gold_expr.
numbers, target and gold_expr are null on every line.
