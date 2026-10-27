# 0.2d gates, ADDENDUM-27: the creative-request rule is removed (Ben). Written 2026-09-26 18:40 UTC, before any code or run

At 18:39:38 UTC Ben chose "Remove" on the card "Remove the hand-written 'creative request' rule from the next build?"
(cmsg_01FuvegZXjMmeUzStiEFVnEWYJNbtPx88nyq6hYLk3Src2). The option read: "One talker path for every message; useful
creative replies drop from 28 to 24 of 60 on the old test."
- The following are removed from 0.2d: D1 (is_creative333c, claude_cre333b_agent.py:45-59), D2 (context_facts,
  claude_cre333_agent.py:53-62) and D3 (k1a's refusal, memory-claim and invented-relative guards, and its fallback).
  There is one talker path for every message. ADDENDUM-15's "k1a joins" is replaced by this. The K1 row now measures
  the one talker path.
- Still open with Ben: how K1 and C1 are judged against Qwen3.5-2B and LFM2.5-1.2B. Option (a), no-harm against plain MiniCPM with Q and L
  reported, is recommended. Until he rules, ADDENDUM-15/21's bars stand as written. The LFM creative-writer test k1f
  runs as a test only; any build switch to LFM goes back to Ben.
- For the record: at 18:39 Ben approved dl-7b ($1.00, the H-B candidate) and the note-writer retrain ($0.65, after
  gate3 passes).
