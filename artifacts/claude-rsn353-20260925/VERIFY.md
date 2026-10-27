# rsn-353 verification (sleep research thread, 2026-09-25 19:30 UTC)

**rsn-353 = registered FAIL, but the loop now learns.** Rental re-run (rsn-353b, $1.37). The Director recounted
from the result files; my own recount from by_category agrees.

| mark | bar | s1 | s2 |
|---|---|---|---|
| L1 last copy action_ce | ≤ 0.05 | 0.118 FAIL | 0.039 PASS |
| L2 fresh panel296 total | ≥ 215 / ≥ 207 | 210 FAIL | 208 PASS |
| L3 invented (checked) | ≤ 2 each panel | 0 / 0 PASS | 0 / 0 PASS |
| L4 dev at 6 / 12 / 20 rounds | report | 902 / 901 / 899 | 890 / 888 / 777 |

- Shown: removing the random per-pass vector fixed the copy phase (296 loop: copy loss 1.85 / 1.97, fresh
  106 / 101; now 0.13 / 0.04 and 210 / 208). "Proved wrong" (L1 > 0.5 both seeds) did not trigger.
- The loop is still below the plain net (225 / 217): counting 5 and 4 of 30 (plain 12), three-step 0/30.
- Thinking longer does not help: flat from 6 to 12 rounds, and seed 2 drops at 20 (more "I don't know").
