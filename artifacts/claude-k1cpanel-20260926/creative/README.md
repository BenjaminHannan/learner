k1cpanel (TEST-ONLY, blind). Counts only. Do not quote, train on, or tune on these items.

File: items.jsonl (JSON Lines, 100 lines, ids kq-001 .. kq-100 in order)

Kinds:
- idea: 70
  - 35 with exactly 1 lead-in turn
  - 35 with 0 lead-in turns
- uses_facts: 30
  - 10 with 1 teach turn
  - 10 with 2 teach turns
  - 10 with 3 teach turns

Fields per line (exactly 8): item_id, kind, turns, last, facts, numbers, target, gold_expr
- numbers, target, gold_expr: always null
- facts: empty list for idea items; non-empty list of {owner, relation, value} for uses_facts items
