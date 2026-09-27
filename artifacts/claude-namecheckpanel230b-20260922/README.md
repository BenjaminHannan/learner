# TEST-ONLY: name-check panel for exp 230b

TEST-ONLY. Builders must not open, print or tune on this folder before sealing their own work.

40 items, each a fresh session (setup turns, then one question). All names are fictional.

| family | count | expect |
|---|---|---|
| mismatch | 12 | NO |
| match | 8 | YES |
| untaught | 6 | NOT_TOLD |
| casual | 6 | YES x3, NO x3 |
| controls | 8 | UNCHANGED |

## Files
- panel.jsonl: fields id (n230b-001..040), family, setup (list of turns), question, expect, gold_name (stored name or null), note.
- base230.jsonl: {id, base_reply}, the final-turn reply of base scripts/claude_loop230_agent.py with artifacts/claude-yesprefix230-20260922/loop230-config.json, one fresh workdir per item. All setup turns saved on the base. Items were not changed after seeing base replies.
- SEAL.sha256.txt: sha256 of panel.jsonl and base230.jsonl.

## expect values
- YES: reply starts with "Yes" and gives the stored name.
- NO: reply does not start with "Yes"; should give the stored name.
- NOT_TOLD: reply does not start with "Yes".
- UNCHANGED: reply equals the base reply.
