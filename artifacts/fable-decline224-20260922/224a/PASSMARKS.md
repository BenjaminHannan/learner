# Exp 224a PASSMARKS (scorer side only; no agent change) — sealed before the registered run

Detector: scripts/fable_decline224.py `is_decline(reply)`.
Re-scorer: scripts/fable_rescore224.py (stored rows only; each frozen scorer's
abstain/clarify check swapped for is_decline by monkeypatch or verbatim verdict
copy; no frozen file edited). A2 checker: scripts/fable_decline224_a2.py.

The three 224b sentences are fixed in fable_decline224.py BEFORE this seal:
- Q1 "I don't know that yet — you haven't told me."
- Q2 "I didn't understand that question — could you say it another way?"
- S1 "I didn't understand that well enough to save it — could you say it another way?"

## Marks
- A1: re-scoring the stored 138i rows (artifacts/fable-agent138i-20260922, excluding
  g1bench-h which holds 138h rows) AND the stored 138h rows
  (artifacts/fable-agent138h-20260922) gives 0 verdict changes (FROZEN check vs
  is_decline on the same row) on every suite: rt136, rt143, sessions152, bench
  new_121_4hop / old_s2fresh_4hop / bench132_4hop / edit200, marks123 stored rows
  (bench edit_200 + s2fresh_4hop, rt81). Also required: sanity_mismatch 0 (the
  FROZEN recompute reproduces every stored verdict).
  marks123 rt110 is re-scored INFORMATIONALLY only (outside this bar: it is outside
  the suitediff marks123 subset p4/q1/bench/rt81); its change count is reported.
- A2: is_decline accepts 45/45 census texts and 3/3 new sentences, rejects 7/7
  self-CANNOT answers, and rejects 100/100 sampled real replies (first 50 distinct
  "Saved:" teach replies of the 138i rt143 rows + first 50 distinct bench-correct
  answers of the 138i edit200 rows) — bar: all accepted as listed and >= 50 real
  replies rejected with 0 real replies accepted.

Verdict 224a = PASS iff A1 (both bases) and A2 pass.

## Pilot-driven design decisions (made BEFORE this seal, from the pilot on these same rows)
- Self-router CANNOT answers ("I have no opinions.", "I cannot predict.", ...) are NOT
  declines (the brief listed them in the census). Counting them moved rt143 J8/K9/O5
  (a self-router misroute "What is the capital of Ostmark?" -> "I have no opinions.")
  from WRONG-ANSWER to OK/MISSED.
- rt81 "must" strings are content checks, not abstain checks: not swapped (swapping
  "another way" -> is_decline moved 3 rows).
- rt110 is informational: its frozen ABSTAIN_BITS lacks "was that a question" while the
  bench and rt143 lists contain it; the union moves N6 BUG->OK on both bases.
- A1 on these rows is a compatibility check that the pilot already saw pass; it is
  not independent evidence.
