# 0.2d gates, ADDENDUM-34: dl-7b FAIL, H-B still open. Written 2026-09-26 20:14 UTC

Fix sleep reported at 20:14 UTC, and I checked it against artifacts/claude-dl7-20260926/VERIFY.md (a1ce6187b). dl-7b is a
registered FAIL on F3: it kept 263 of the learning against a bar of 276, which is 76% where 80% was needed. F1, F2,
F4 and F5 pass, and forgetting fell from 26 to 7 panel items. No sleep recipe has passed both forgetting and learning,
so H-B stays open and SLEEP02D stays empty.
What comes next, from Fix sleep:
- dl-5s, a CPU finding, running now;
- dl-9, a learned on/off switch that keeps the night's add-on off questions that are not its kind. It is registered
  and runs first on BensPC after 358i2;
- dl-8, error-gated nights (1771eba18), sealed and queued on BensPC.
Whichever passes fills the slot in its own form (ADDENDUM-32). No mark changes.
