# TEST-ONLY: exp 230b-r name-check panel

TEST-ONLY. Do not open, print or tune on these items while building or piloting the 230b fix.
Written blind (without reading the 230b agent, scorer, results, or the old 230b panel).

- panel.jsonl: 48 items, one fresh session each. Fields: id, family, setup (turns sent first), question, expect, gold_name, note.
  Families: mismatch 14 (NO), match 10 (YES), untaught 6 (NOT_TOLD), casual 8 (4 YES, 4 NO), controls 10 (UNCHANGED = same reply as base).
- base230.jsonl: base agent scripts/claude_loop230_agent.py + artifacts/claude-yesprefix230-20260922/loop230-config.json, fresh workdir per item.
  Fields: setup_replies, base_reply, stored triples, base_yes (base reply starts with "Yes"), yes_item_not_yes_on_base.
  The "YES keeps Yes" mark counts only YES items with base_yes = true (11 items). Three YES items do not start with "Yes" on the base; they are kept and flagged.
- Every setup name statement saved on the base; no replacements were needed. The base run was repeated once and gave identical output.
- Fictional names only. SEAL.sha256.txt holds the hashes of panel.jsonl and base230.jsonl.
