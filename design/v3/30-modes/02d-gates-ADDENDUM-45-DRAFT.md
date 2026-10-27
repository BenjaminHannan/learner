# 0.2d gates, ADDENDUM-45 DRAFT (NOT IN FORCE): sleep moves to the reasoner; the talker gets no skill nights. Written Sun Sep 27 13:27:17 UTC 2026

Month-end. Additive only. No 0.2d code is sealed and nothing has run. This draft changes nothing yet.

## Why it is a draft
- The Thread manager (13:28 UTC) relayed Ben's words in its thread:
  - 13:25:42 UTC: "isn't it supposed to be the reasoner? Why would the talker need to be trained at all? It just talks"
  - 13:26:04 UTC: "that's like saying google translate every night should train on how well it translated"
  It took them as his yes unless he says stop.
- Moving the H-B gate from a talker adapter to the reasoner is an architecture change (goals page :96), which only Ben
  approves. His two lines are questions. The coordinator (13:26:54 UTC) asked this thread to hold until the Thread
  manager confirms his explicit words.
- This file goes in force only through a later addendum that quotes Ben's explicit yes to this change.

## What changes once in force
- H-B and SLEEP02D mean the reasoner's nights, owned by Sleep research. The registered PASS on small nets is slp-358n2
  (artifacts/claude-slp358n2-20260926/RESULTS.md: M1-M3 on both seeds, CPU). H-B is no longer an adapter on the
  talker 1B, and dl-3's marks on the talker no longer define it. The new H-B marks are Sleep research's, fixed in that
  addendum before any 0.2d seal.
- Z1 goes: no talker nights on code-made number puzzles. scripts/claude_e2e02d.py's sleep line (:25-28), SLEEP02D (:75)
  and the talker adapter loader (:171-177) change to load the reasoner's slept weights, in the in-force addendum.
- The talker is trained only on talking, if at all. The one talker item already named stays owed: H1, the talker
  learning to read the reasoner's output.
- Fix sleep's talker results stand as findings (dl-6, dl-7b FAIL; dl-9 PASS on its own marks, ADDENDUM-44). None of
  them enters 0.2d under this change.
