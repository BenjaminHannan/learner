# rt-02h ADDENDUM 1 (2026-09-26 16:07 UTC, before any head is trained or any run)

Ben chose "Redirect" at 16:04 UTC (see design/v3/30-modes/ben-goals-2026-09-26.md): no new work goes into rule-based
puzzle or routing gates, and the next build is judged against plain same-size models. This addendum changes only the
decision rule. Marks H1-H4, the arms, the test panel and the machine are unchanged.

- D (rt-02d rules) and E (rt-02e) stay in the score. D is still part of H1's sealed bar; otherwise both are report-only
  baselines. rt-02e itself is stopped (artifacts/claude-rt02e-20260926/STOPPED-rt02e.md).
- New decision rule: if rt-02h passes H1-H4, it is the chat decider and copier for sum puzzles in the learned design.
  Month-end joins it as its own single change. The old "no more fires than E" condition is dropped.
- If it fails, the FAIL stays a FAIL. The next test starts from "how does the brain decide that someone is asking it to
  solve something?" (Ben, cmsg_01FuvegZXjMmeUzStiEFVnEWMWVJnvL8azz8YgCn21XSC8) and is one sealed single change.
