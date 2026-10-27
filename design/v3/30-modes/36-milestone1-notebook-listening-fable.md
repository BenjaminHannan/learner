# Milestone 1 — notebook contract + LISTENING (Fable, 22 Sep 2026)

Built as plain software, no model: `scripts/fable_notebook_contract.py`, `scripts/fable_listening_m1.py`.

**Checks run**
- 30-sequence lifecycle suite: contract notebook 30/30; a naive last-write-wins notebook fails 27/30 (so the tests test something).
- Mutation check: 7 deliberate breakages (anyone writes taught, inferred ignores dependencies, newest beats taught,
  silent overwrite, guesses answer, no tamper check, auto-merge of same names) — all 7 caught.
- LISTENING: 33-turn scripted conversation + restart — pass. Covers save-then-say-saved, conflict → ask → yes/no,
  two Miras → "which one?" → pick, quotes write nothing, dropped pending question, forget, broken chain, unknown person.

**Known limits (on purpose)**
- Input is structured lines (`teach Mira city = Lisbon`), not English; multi-word names only through `alias`.
- Every relation is single-valued unless declared otherwise. No dates, numbers-as-numbers, negation, or "used to".
- Not yet wired: the frozen lookup operator from M0 (answers come from the software hop loop), the scheduler, other modes.
- Tests were written by the same author as the code; Ben's 30 natural turns are the independent check (pass mark 27/30 representable).

**Next:** Ben's 30 turns → hand-map into this schema → fix gaps; then scheduler conformance suite.
