# followup_ab result (card experiment only)

Run 2026-10-24 on one rented Vast box (V100, 40 cores, ~$0.11/hr, ~1.2 h incl. a re-run whose log lines were truncated; total ~$0.15; box destroyed). Seeds 0,1; 5000-item test set; chance 12.5%. JSONs in results/.

| variant (one change vs base) | B real (A->B) | B shuffle | B mean | probe v: msg | reg0 | all regs | bag control | A real (B->A) |
|---|---|---|---|---|---|---|---|---|
| base (pooled, 8k steps) | 41.1 | 12.3 | 13.3 | 41.0 | 40.8 | 39.9 | 41.3 | 100 |
| steps3x (24k steps) | 41.3 | 12.0 | 12.9 | 40.7 | 41.0 | 39.9 | 41.3 | 100 |
| timing (3 loops, send after 2) | 35.0 | 12.3 | 12.1 | 41.0 | 40.8 | 39.9 | 41.3 | 100 |
| fullread (sender attends over all of A) | 35.3 | 12.1 | 12.8 | 41.2 | 40.2 | 40.6 | 41.3 | 100 |
| auxv (diagnostic: local loss on v) | 40.1 | 12.6 | 13.2 | 41.2 | 40.6 | 39.4 | 41.3 | 98 |
auxv's own v head: 40.9% (= bag control).

**Pass marks (PREREG):** no variant passes (all B real < 90%, probe < 80%).

**Verdict (shown):** the bottleneck is computing v, not sending it. Every probe of v, anywhere in A, equals the bag-of-values control (~41%: "v is one of the 4 values present"), and even a direct local loss on v (auxv) leaves A's own v head at the bag level. So A never learns the name-to-value lookup at this size and training budget; the bridge faithfully carries what A has (the bag: shuffle and mean drop B to chance). Longer training (3x), more loops before sending, and letting the bridge read all of A change nothing.
**Suggested:** the A->B failure is a small-reader binding problem (find the value next to the queried name), not a bridge problem. Untested: an A with more layers/heads or an induction-friendly curriculum (few entities first).
