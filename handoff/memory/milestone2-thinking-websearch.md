---
name: milestone2-thinking-websearch
description: 2026-09-22 THINKING/LEARNING mode v1 built as plain software with real web search via the GPT bridge; findings quarantined until Ben approves
metadata:
  type: project
---

scripts/fable_thinking_m2.py (notes: design/v3/30-modes/37-milestone2-thinking-websearch-fable.md). Self-test 18/18 incl. hostile pages; one real search ("the moons of Mars") quarantined 8 NASA-sourced findings. Commands: assign / think / review / approve Fxxxxx / reject / approve-topic.

**Gotcha:** the claude-web bridge replies in escaped Markdown (`\[`, `\_`, `[url](url?utm_source=...)`); `parse_bridge_reply` undoes it. Reuse that function for any JSON asked of the bridge.

**Limits:** quotes not re-verified against the page; literal values only; no relation normalisation; curiosity = suggested-topic list only. Builds on [[milestone1-notebook-listening]]; web search is a tool per [[placeholder-english-ok]].

**Update 2026-09-21 (v1.2):** first real run believed 0/8 (bridge drops the backslash in \" → whole reply unreadable; fixed with item-by-item reading + FABLE_BRIDGE_LOG). Second real run believed 3; after adding number+unit matching to 2 significant figures (_value_key) the same saved findings give 6/6 believed from 2–4 independent sites each. Gaps: Wikipedia quote check often fails, no unit conversion, no hostile-topic test on the live web yet.
