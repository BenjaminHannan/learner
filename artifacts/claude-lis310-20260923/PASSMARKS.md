# lis-310 PASSMARKS (sealed BEFORE the registered run, 2026-09-23)

Build: 291 + the lis-300 listener (turn310 outside turn291). CPU build.
Tests: scripts/claude_lis310_test.py, StubReader (no weights), threshold 0.99
(lis-300 THRESHOLD.txt default; no THRESHOLD.txt on origin/main as of today).

## Marks

| Mark | Bar |
|---|---|
| P310.1 all sealed unit tests pass | 11/11 PASS, exit 0 |
| P310.2 base-chain writes in the blocked-write test (T7) | 0 writes over 5 turns |

## Predicted moves (from the pilot, same sealed files)

- T1 "My sisters are Mira and Tal." (STATE, 2x ASSERT me, conf .999) saves 2
  triples (USER,sister,Mira) + (USER,sister,Tal); reply is the base mouth's
  save confirmation ("Saved: your sister is ...").
- T2 "Our dog is Pip." (we-frame) replies exactly
  "Whose dog is Pip, yours or someone else's?"; 0 triples.
- T3a low-conf STATE (conf 0.5 < 0.99) replies exactly
  "Just to check: is Mira's dog Pip?"; 0 triples; then "yes" saves exactly 1
  triple with a Saved reply.
- T3b same ask-back, then "no": 0 triples, "Okay, I won't save that."
- T3c same ask-back, then another fact turn: pending dropped, new turn saves
  normally (1 triple, the dog fact never saved).
- T4 NEGATE turn saves 0; reply is the base's (no write).
- T5 CHECK "So Mira's dog is Pip." after a STATE teach: base answers
  "I already have that."; triples unchanged (1); 0 new events.
- T6 "Whose dog is Pip?" (ASK frame) answered from the notebook
  ("Mira's dog is Pip. (worked out backwards)"); 0 new events.
- T7 5 rule-chain-teachable turns (SUPPOSE / NEGATE / PLAN / REPORTED-held /
  CHECK frames over plain teachable sentences): each verified to grow
  notebook events on the raw 291 base first, then 0 events growth and 0
  triples under 310; total base-chain writes 0.
- T8 unparsed frame (None): exact "Sorry, I didn't catch that. Could you say
  it another way?"; 0 triples.
- T9 fable_marks123_all.load_agent finds Loop310Daemon + build_agent310 +
  DEFAULT_CONFIG310 (lis310 key); the demo's server-style build runs a
  mailbox turn and saves 2 triples.

## What FAILS the run

Any test FAIL, any base-chain write in T7, any post-seal change to a sealed
file (seal = artifacts/claude-lis310-20260923/SEAL.sha256.txt), any real-model
turn (weights unavailable; StubReader only).
