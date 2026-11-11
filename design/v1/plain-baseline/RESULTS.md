# Plain-transformer baseline — RESULT (2026-10-23)

Pre-registration: design/v1/plain-baseline/PREREG.md (before any code). Vast RTX 4090, 12,000 steps, $0.78 (plus $0.30 for a
first box that tripped the memory guard at step 50 and $0.16 for one that never booted). Raw: results/plain/final_dev.json.

| Model (same village data, same questions) | dev (42,653 q) | validation, held-out (8,675 q) |
|---|---|---|
| plain transformer, 2,022,912 params | 33.1% | 22.0% |
| V1 FLOOR (Vast results2) | 68.4% | 30.9% |
| V1 FULL (Vast results2) | 80.1% | 44.7% |

- M1 "FULL's edge shown" needs FULL validation - plain validation >= 5.0 against BOTH comparators. Against the Vast FULL:
  44.7 - 22.0 = +22.7 points -> met. The v1full-pc re-run comparator is still pending, so M1 is
  not final until that number is in.
- Sanity (dev >= 8.95% + 10): 33.1% -> passed (not a wiring failure).
- Caveat: the plain model reads a 736-token window of the visit per question (contender-A input), the token budget is
  matched, one seed.
