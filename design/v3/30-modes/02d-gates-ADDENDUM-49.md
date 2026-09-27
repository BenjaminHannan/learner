# 0.2d gates, ADDENDUM-49: ADDENDUM-46 bans skill nights on the talker, not talking adapters; k1f is not a 0.2d input. Written Sun Sep 27 13:42:46 UTC 2026

Month-end. Additive only. No 0.2d code is sealed and nothing has run.

## Scope of ADDENDUM-46 (Thread manager, 13:46 UTC)
- Ben's yes (13:28:08 UTC) answered "Should the talker stop getting skill training at night, so sleep trains only the
  reasoner?". It bans skill training of the talker. It does not ban an adapter that only changes how the talker talks;
  the Thread manager's 13:24 answer to Ben named "not inventing facts" and "learning to read the reasoner's answer".
- So DOUBT02D (y1t: saying "I don't know" when its answer would be wrong) and mu-406 (answer the present turn, use
  memory only when asked) stay candidates if they pass. H1 stays owed.
- ADDENDUM-46's "the Talker loads no adapter" means no SLEEP adapter. The code docstring now says so. DOUBT02D has no
  loader yet (scripts/claude_e2e02d.py:76 is only the slot); it is written at the seal as before. Wiring selftest 18/18.

## k1f (Creative chat's test, queued as k1f-benspc2)
- Its K and F arms load SLEEP02C_ADAPTER = 0.2c's adapter02c.pt (puzzle-trained sleep adapter on the talker;
  artifacts/claude-k1f-20260926/PASSMARKS-k1f.md:33-36). Under ADDENDUM-46, 0.2d's talker never carries that adapter,
  and since ADDENDUM-27 0.2d has one talker path with no k1a writer.
- Decision: k1f's K and F results are not a 0.2d input, and 0.2d does not wait on them. Its plain arms T, Q and L load
  no adapter, so their counts can still be reported beside 0.2d's K1 row as rival references (option (a), still
  open with Ben). Whether k1f runs at all is Creative chat's call, as its owner.
