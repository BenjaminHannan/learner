# lis-311 PASSMARKS (sealed BEFORE the registered runs, 2026-09-23)

Build: 292 + the lis-300 listener (install_turn310 from
scripts/claude_lis310_agent.py, read-only) with the real Reader.
CPU/MPS build for the Mac. Sealed threshold T = 0.995
(artifacts/claude-lis300-20260923/THRESHOLD.txt). Weights:
~/premonition-models/lis300-merged/, merged-reader sha256
112880d610173aef9b39715e0f6db51a16af8dece42dbd7132b83c0be8285324
(recorded in lis-300's RESULTS.md; verified match 2026-09-23).

Tests: scripts/claude_lis311_try.py --stub (StubReader, threshold 0.995).
Server: scripts/claude_lis311_server.py on port 8767 (own state dir
~/premonition-chat/lis311-state).

## Marks

| Mark | Bar |
|---|---|
| P311.1 every stub scenario passes | 10/10 PASS, exit 0 |
| P311.2 base-chain writes in the blocked-write test (T7) | 0 writes over 5 turns |
| P311.3 the server on 8767 answers a turn | GET / 200 + POST /turn 200 with a reply |

## Predicted moves (from the pilot, same sealed files)

- T1 "My sisters are Mira and Tal." saves 2 triples (USER,sister,Mira) +
  (USER,sister,Tal); reply the 292 base mouth's save confirmation
  ("Saved: your sister is Mira. Saved: your sister is Tal.
  (I also have Mira.)").
- T2 "Our dog is Pip." replies exactly
  "Whose dog is Pip, yours or someone else's?"; 0 triples.
- T3a low-conf STATE (conf 0.5 < 0.995) replies exactly
  "Just to check: is Mira's dog Pip?"; 0 triples; then "yes" saves exactly 1
  triple with a Saved reply ("Saved: Mira's dog is Pip.").
- T3b same ask-back, then "no": 0 triples, "Okay, I won't save that."
- T3c same ask-back, then another fact turn: pending dropped, new turn saves
  normally (1 triple, the dog fact never saved).
- T4 NEGATE turn saves 0; reply is the base's clarify (no write).
- T5 CHECK "So Mira's dog is Pip." after a STATE teach: base answers
  "I already have that."; triples unchanged (1); 0 new events.
- T6 "Whose dog is Pip?" (ASK frame) answered from the notebook
  ("Mira's dog is Pip. (worked out backwards)"); 0 new events.
- T7 five turns (SUPPOSE/NEGATE/PLAN/REPORTED/CHECK city turns): each first
  verified to grow notebook events on the raw 292 base, then 0 events / 0
  triples under 311. Base-chain writes: 0.
- T8 unparsed frame saves 0 with the exact sorry-reply.
- P311.3: GET http://127.0.0.1:8767/ answers 200; one POST /turn answers 200
  with a reply; server left running; 8765/8766 untouched.

## Step 3 try-out (report-only, no bar)

30 scripted casual turns (fictional names; 3 conversations x 10: lowercase,
two facts in one message, "our", a correction, a question, a negation,
small talk) through build_agent311 with the real Reader on the Mac.
After any ask-back the driver sends "yes" (adaptive rows, not in the 30).
Every turn row (turn, reply, saved, frame, confs, ms) lands in
artifacts/claude-lis311-20260923/real-rows/rows.jsonl. Report: all rows,
median/p90/max ms per turn, device (pilot: mps), weights-sha check.
No model-behaviour bar is set: lis-300 is a registered FAIL on recall
(asks back about half the true facts), so ask-backs and held turns are
expected and reported as-is.
