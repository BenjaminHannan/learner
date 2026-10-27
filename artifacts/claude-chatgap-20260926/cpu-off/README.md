# Chat gap, plain-model half (CPU, report only) - Fix sleep, 2026-09-26 13:30 UTC

Diagnosis only: nothing registered, trained or tuned. Plain MiniCPM5-1B (rev 87179e5c, thinking off), NO adapter, on this
cloud CPU, the same 40 code-made chat puzzles as 0.2c's chat measure (claude_chatgap_diag.chat_puzzles). Greedy.
The adapter-on side and the whole-assistant column (C2) need BensPC (queue 006m-chatgap-benspc).

| column | what | solved of 40 | kinds |
|---|---|---|---|
| P1 | puzzle prompt + rule-keeper | 2 | 38 wrong expression |
| P2 | puzzle prompt, no rule-keeper | 0 | 36 wrong expression, 4 other |
| C1 | chat wording straight to the 1B (96 new tokens) | 0 | 36 other, 4 wrong expression |

C1: every reply is 60-72 words, cut off by the 96-token budget in the middle of an explanation ("To solve this puzzle,
we need to use ..."); 4 of 40 contain an "=". So in plain English the 1B explains instead of writing an expression.
Untested: whether a longer budget would reach a right answer (P2's 0/40 without the rule-keeper suggests rarely).
Files: rows_off.jsonl (all replies), run_off.py (the script).
