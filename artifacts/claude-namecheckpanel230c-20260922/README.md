# Exp 230c name-check panel — TEST-ONLY

TEST-ONLY. Do not tune on these items. Blind panel written 2026-09-22 by a separate writer agent. All names are fictional.

## Files
- `panel.jsonl` — 54 lines, one item each.
- `base230b.jsonl` — 54 lines, one per panel id: the base agent's replies.
- `SEAL.sha256.txt` — sha256 of both jsonl files (repo-relative paths).

## panel.jsonl fields (exactly these, no others)
- `id`: "c230-001" … "c230-054"
- `family`: one of mismatch, match, odd_mismatch, odd_match, untaught, controls
- `setup`: list of strings (teach turns, sent before the question)
- `question`: string (final turn)
- `expect`: one of NO, YES, NOT_YES, NOT_NO, NOT_TOLD, UNCHANGED
- `gold_name`: string or null (the stored name)
- `note`: string

Families: mismatch 12 (NO), match 8 (YES), odd_mismatch 12 (NOT_YES), odd_match 8 (NOT_NO), untaught 6 (NOT_TOLD), controls 8 (UNCHANGED).

## base230b.jsonl fields (exactly these, no others)
- `id`
- `base_reply`: reply to the question
- `base_setup_replies`: list of replies to the setup turns
- `stored`: list of [s, r, v] notebook triples after the question
- `base_yes`: bool, true when base_reply starts with "Yes"

Base: scripts/claude_loop230b_agent.py with artifacts/claude-namecheck230b-20260922/loop230b-config.json, run through the scratchpad probe runner (dialog_nb.py), one fresh workdir per item. Every setup name statement saved on the base (no replacements).
