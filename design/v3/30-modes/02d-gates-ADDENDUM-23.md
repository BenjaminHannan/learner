# 0.2d gates, ADDENDUM-23: recall store v4. Written 2026-09-26 17:31 UTC, before any run

Offer from Trustworthy notes. rd-378u PASSED, verified with a blind recount (f4edf55ac): on unseen LoCoMo chats 5-9 an
evidence line reached the top 10 for 585 of 772 questions, against 489 heard-only.
- 0.2d's recall store is scripts/claude_ep382_store_v4.py (EP382_STORE=claude_ep382_store_v4). A note is used only as
  a pointer to the raw lines it cites; answers read raw lines only. This matches Ben's "notes are pointers to the raw
  chat", and it is how the brain's hippocampal index points to stored episodes rather than holding the answer. That
  comparison is a guess.
- With no note rows, v4 returns exactly what v3 returns. Month-end checked this in the code: the selftest line
  "no notes: identical to v3" (scripts/claude_ep382_store_v4.py:77). So under fallback N0 (ADDENDUM-20) this changes
  nothing.
- The notes that fill it come only from the GLM-trained writer (rd-378g, sealed marks in artifacts/claude-rd378g-20260926/)
  once it has a verified PASS. The rd-378 writer never ships (16:53 ruling). No row or bar changes.
