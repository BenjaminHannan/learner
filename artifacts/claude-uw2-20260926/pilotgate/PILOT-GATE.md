# uw-2 pilot gate on lis-320 pilot 8 (ADDENDUM-2 item 3): PASS, 60 of 60 (checked 2026-09-27 10:17 UTC)

- Cards: scripts/claude_uw2_data.py build on artifacts/claude-lis320-20260926/pilot8e (seed 328, 60 Luna chats,
  origin/builder-outbox). build.json holds the counts: 404 cards, 290 in the mix, 58 corrections (19 correct_ref),
  232 NONE; skipped 10 turns not kept, 1 correction whose old fact is not a note, 0 value-not-span drops.
- Draw: gateprep, seed 4053. That gave 60 packets: 30 corrections (15 correct_ref) and 30 look-alike NONE cards.
- Judges: two fresh blind agents, each with JUDGE-gate-uw2.md verbatim and only its own copy of packets.jsonl. Each
  wrote 60 answers (judge1.jsonl, judge2.jsonl).
- gatecmp gave 0 splits (so no third judge) and 60 of 60 agreeing with the code label: 30 of 30 corrections and 30 of
  30 NONE.
  - Blind recount by a separate script, not gatecmp: judge 1 agrees on 60 of 60 and judge 2 on 60 of 60. On all 30
    corrections, judge 1's new value equals the code value exactly.
- Verdict: PASS (bar 54 of 60). Pilot cards are never trained on. The full gate still runs on the seed-324 training
  cards with new judges.
