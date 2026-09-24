# 333b: creative with thinking off. Marks fixed 2026-09-24 ~17:45 UTC, before 333b produces any panel reply

One change from 333: Gen333b (scripts/claude_cre333b_agent.py) renders the chat template with enable_thinking=False
and cuts any leftover think text. Routing, prompt, 11 candidates, filter and pick are 333's, unchanged.
Dev evidence (not the panel): on the CPU with the real MiniCPM5-1B, 3 DEV creative requests: 0/33 candidates had
think text, 1 to 5 of 11 dropped by the filter, a pick every time (333: 10/10 DEV fallbacks).
Arms: P = 292t + 333 with Gen333b (scripts/claude_cre333b_wrap.py b); B = 333's registered arm_B.jsonl (292t alone,
unchanged code); T = twin b. Same panel (creativepanel333, TEST-ONLY), same scorer, same judge instructions.
Marks and bars: P333.1-P333.5 exactly as in PASSMARKS.md (P333.2 is expected to FAIL again: routing is unchanged).
Report only: fallbacks, P's candidates dropped. Proved wrong if P's useful count is still below 16/40 (thinking was
not the main cause).
