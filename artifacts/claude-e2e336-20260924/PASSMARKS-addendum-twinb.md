# 336 addendum (month-end thread, 2026-09-24 ~17:20 UTC, before 336 has run)

The plain twin in 336 is twin b: scripts/claude_e2e336_twinb.py, run through scripts/claude_twinb_wrap.py
(`python -B scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py --arm twin ...`). Why: the old twin never
turned off MiniCPM5-1B's thinking mode; in the 338 run all 400 of its replies started with a think block and 201
never finished (artifacts/claude-chat338-20260924/VERIFY-338.md). Twin b is identical except for
enable_thinking=False and cutting leftover think text. This makes the twin stronger, so every "beats the twin" mark
(M6) gets harder, not easier. No mark, bar or panel changes.
