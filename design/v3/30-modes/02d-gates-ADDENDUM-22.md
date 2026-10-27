# 0.2d gates, ADDENDUM-22: no rule-made confirm questions. Written 2026-09-26 17:13 UTC, before any run

Lead from Trustworthy notes (44c4b4341, artifacts/claude-trustnotes-20260926/LEAD-ch403-save-after-goodnight.md): in
ch-403's DEV run the 0.2c build asked "is Kim's occupation marine biology?" when no Kim had been mentioned. The
hand-written confirm-question path (claude_lis310_agent.py) turns any frame below the bar into a question, even when
nobody ever said who owned it.
Decision (Month-end, under Redirect): 0.2d does not carry that path. A frame below the bar is neither saved nor
turned into a question, and the talker's replies come from the talker alone. The save half (acknowledging after a
question does not save the fact) is lis-320's, sealed by Reading facts. A learned "ask to check" is later work that
needs its own test. No row or bar changes.
