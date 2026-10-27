# 0.2d gates, ADDENDUM-46: sleep moves to the reasoner; the talker gets no skill training. Written Sun Sep 27 13:29:12 UTC 2026, before any seal

Month-end. Additive only. No 0.2d code is sealed and nothing has run. This puts ADDENDUM-45-DRAFT (de662fa63) in force,
with the change below on switches.

## Ben's words (checked with fetch_messages)
- 13:25:42 UTC (cmsg_01FuvegZXjMmeUzStiEFVnEWV8GYuEZQFfD7RG1sBayTH4): "isn't it supposed to be the reasoner? Why would
  the talker need to be trained at all? It just talks"
- 13:26:17 UTC, the Thread manager asked "Should sleep move to the reasoner?" (cmsg_01FuvegZXjMmeUzStiEFVnEWThGGksDRZE6LHV44o6ndeq;
  its last edit, 13:27:19, came before Ben's answer). It named the change: Month-end points the build's sleep gate at
  the reasoner's nights, which Sleep research owns; a switch inside the reasoner is left to the experts card.
- 13:28:08 UTC, Ben: "yes" (cmsg_01FuvegZXjMmeUzStiEFVnEWF3UMqBUcaQoQMBxSh17FDr).

## What changes
- H-B and SLEEP02D mean the reasoner's nights, owned by Sleep research (small-net registered PASS: slp-358n2,
  artifacts/claude-slp358n2-20260926/RESULTS.md). SLEEP02D is the reasoner's slept checkpoint. Sleep research fixes
  the new H-B marks in its own sealed plan before any 0.2d seal; dl-3's talker marks no longer define H-B.
- Z1 is out: no talker nights on code-made number puzzles.
- The talker gets no skill training. The owed H1 hand-off (the talker learning to read the reasoner's output) is the
  only talker training already named, and it stays owed.
- Fix sleep's talker results stand as findings (dl-6, dl-7b FAIL; dl-9 PASS on its own marks, ADDENDUM-44). None
  enters 0.2d.
- Not decided here: a switch between separate parts inside the reasoner (the experts card is still open).

## Code (scripts/claude_e2e02d.py, unsealed draft)
- The header's sleep line now says the above; Z1 is gone from it.
- The Talker loads no adapter. The SLEEP02D check moved from Talker.__init__ to solver_for: a set SLEEP02D stops the
  run until the reasoner-nights loader is written at the seal. Wiring selftest: PASS 18/18.
