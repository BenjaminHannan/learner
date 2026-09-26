# corrpanel401 (sf-401 correction panel, TEST-ONLY)

Written blind to artifacts/claude-sf401-20260926/PANEL-SPEC.md by four writer agents (6 lives each, parts p1-p4,
disjoint name letters), merged by scripts/claude_sf401_audit.py merge. Not to be trained on, tuned on, quoted or
read by builders; only the runner (claude_e2e336_run.py), the scorer (claude_e2e336_score.py) and the sf-401 judge
packets read it. No items are quoted here.

Counts (scripts/claude_sf401_panelcheck.py, ALL CHECKS PASS):
- 24 lives x 3 days, 610 user turns: teach 196, correct 70, nosave 42, smalltalk 71, ask 231.
- Asks: one_hop 68, two_hop 25, reversal 20, edit 74 (one-hop value 32, two-hop 26, yes/no 16), yesno 24,
  never_told 20. Day-3 asks on uncorrected day-1 facts: 80.
- Truth: 468 facts (70 closed by a correction). Correction styles 1-6: 12, 11, 12, 11, 12, 12.
- Decoys (48; leave their fact unchanged, each checked by a later non-edit ask): second_value 11,
  same_value_other_person 11, visit_not_move 9, past_said_as_past 8, plan_or_question 9.

Blind audit (a separate agent answered all 231 asks from the user's words alone, without the key, then compared):
231 of 231 agree, 0 key fixes, 48 decoys reviewed, 0 reworded. Files unchanged by the audit (sha256 below).
- turns.jsonl 0efd2e1392951ebb275164c5c99e91ee5dcedfadd4edc6b2e43dedd9afbe1ae4
- truth.jsonl d1ca8e308ddeb6394b7f6fa4d5341cff66821dc02db32e2eabb493f4b8f51096
- decoys.jsonl 2b20db529cacdf1a0d697cd25c2a0943a2682cc18bbc01915faad29e24c790d7
- corrections.jsonl 1986b15ed6f109563ccae580a5ac0d825acdf3b7d8d37d491470f93de72bab18
