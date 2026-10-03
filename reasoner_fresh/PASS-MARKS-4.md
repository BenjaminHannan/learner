# Decision rule for the 6-seed "think before calling" test, fixed before the new runs (2026-10-03, fast lane)

Seeds 0-2 already exist (PASS-MARKS-3 results, seen before this rule was written, so they are exploratory).
New runs: seeds 3, 4, 5 for both arms (copy-only vs copy + call after 2 rounds), same code, same sealed eval, same budget.
Per seed: gain = delay-arm right-call rate on new-wording questions (96) minus copy-only rate, same seed.

PASS: over all 6 seeds, paired mean gain >= +4 points AND the 95% t-interval (n=6, t=2.571, SE from the 6 paired gains) lower bound > 0;
 AND on the clean seeds 3-5 alone the mean gain is > 0.
FALSIFIED: 6-seed paired mean gain < +2 points.
Between: anything else; partial, no claim.
Standing numbers reported for future marks: copy-only baseline mean, SD, min, max over 6 seeds of new-wording right-call rate and of
overall final accuracy; same for the delay arm. Per-question rows copied back and counted (192 per run, 1152 total) before destroying.
