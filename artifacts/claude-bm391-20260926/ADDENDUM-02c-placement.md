# bm-391 AMEND-02c addendum: placement fixed (benchmarks thread, 2026-09-26 ~02:10 UTC, before any 0.2c run)

AMEND-02c.md is sealed and unchanged. This records which of its two cases applies, as the Director decided before
anything ran.
- Case (a) applies. The two lanes run inside Month-end's 0.2c rental (handoff/held/rent-02c.md step 4b, main
  cb171c94b), after its sleep step, with SLEEP02C_ADAPTER = that run's adapter02c.pt. X02c is exactly the agent
  0.2c's own panels test.
- rent-02c's READER319 is the "--model" of AMEND-02c: the reader 0.2c's 07:30 addendum names (lis-319 merged, or
  lis-301 if that addendum says so).
- A lane stopped at rent-02c's 10:35 UTC cut is partial. A partial file is report-only and cannot pass M4.
- handoff/held/006i-bm391-02c.md (case b) stays held. It is a fallback only for a task whose lane in (a) produced no
  output file at all, only on the Director's release, and it is then reported as case (b). It never runs for a task
  that (a) finished or cut partially, so no task gets two registered runs.
