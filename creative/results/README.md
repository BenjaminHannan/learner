# creative/results

- `pilot-s100/`, `pilot-s101/`: pilot 1 on the Mac (10-06): old signal gate (rules share >= 0.50), ladder 1,500 / 3,000 / 6,000 plus fallback (a). Every rung failed that gate (rules share 0.25-0.31 at every temperature); the value-blind follower's own share is 58%, so that gate was the wrong measure.
- `pilot2-s100/`, `pilot2-s101/`: pilot 2 (rewritten gates, 1,500 rung, PLAIN sampler): gates pass, PC gate fails on both parents. Kept as the labelled plain-sampler comparison; never pooled with masked arms.
- `pilot3-s100/`, `pilot3-s101/`: pilot 3 (same, MASKED sampler = level-4 used-number + exact-division mask), once run.
- `legal-probe/`: PR #45's read-only probe of why tries break the rules and what the mask does.

Note on honesty: the gates were rewritten, and the marks re-scaled, after seeing DEV numbers from pilot 1 (a feasibility check, not a claim). PC's +2 points on the first (failed) warm-up was known when the marks were re-scaled. T1 and T1b stay sealed. See creative/README.md, "Gates and marks rewritten 10-06".

The level-4 mask is disclosed test scaffolding chosen after the DEV numbers; the same sampler runs for every arm, so it favours none; T1 and T1b were never read.
