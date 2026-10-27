# VERIFY rt-02d: PARTIAL (rental infra), not rerun (2026-09-26 17:17 UTC)

Owner: Plain-English puzzles thread. The rental report is on origin/builder-outbox at 0b80b5fac:
artifacts/claude-rt02d-20260926/RESULTS-rent.md, runs/rent-rt02d, plus a ledger line. The results are checked here
against that report; nothing else came back.

- Setup S1-S6 was all green. BASE is 87179e5c. The reader was copied from the Director's depot with matching sha
  e688e1b2. The adapter sha a33211dc matched, the seals were OK and the selftests passed 55/55.
- The dev determinism gate PASSED: B0 ran twice on the 55 dev rows with 0 differing replies.
- The first registered step (panel B0) started 16:26 UTC. The rental's ssh proxy died at about 16:31 and a reboot did
  not bring it back. Nothing came back from the panel, and no later step ran (each registered step is launched once).
- Spend: 3 rentals, about $1.23 of the $1.50. The destroy was confirmed, and the ledger line is on builder-outbox.
- **Outcome: PARTIAL. There is no registered PASS or FAIL.** Code on the rental read the rt-02d blind panel, but no
  person or model saw its text, and no result exists.
- Not rerun: at 16:04 UTC Ben chose "Redirect", so no new work goes into rule routes. Month-end has also stopped the
  rule puzzle route for 0.2d. A rerun would be new spend on a rule route.
