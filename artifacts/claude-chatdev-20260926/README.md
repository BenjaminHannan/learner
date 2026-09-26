# Everyday-chat DEV practice chats (everyday-chat thread, 2026-09-26)

Ordinary DEV data: anyone may read, quote or tune on it. Written by three separate writer agents (one per part file)
from design/v3/30-modes/382-panels-spec.md + 338-chat-panel-spec.md, 20 conversations each, names A to M (TEST panels
use N to Z). Checked with scripts/claude_chatdev_check.py: CHECK OK.

- Conversations: 60 (dev02e-chat-01..60), 336 turns
- Kinds: smalltalk 51, advice 78, explain 64, feelings 32, followup 49, think 33, teach 15, ask_known 8, ask_unknown 6
- Files: part1.jsonl, part2.jsonl, part3.jsonl (382 chat format: {item_id, turns: [{text, kind, facts, gold, gold_number}]})
Used by ch-403's diagnosis (artifacts/claude-ch403-20260926/DIAG.md) and its DEV gate.
