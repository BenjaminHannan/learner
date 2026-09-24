# rsn-296b verification (reasoning thread, 2026-09-24)

**296b = registered FAIL.** P296b.2 fails on both seeds for comparing: 93/200 and 88/200 vs 160. P296b.4 fails on seed 1: 226 vs 228. P296b.1, P296b.3 and P296b.5 pass on both seeds.

The run seal has 4 lines, and the files were copied back before the instance was destroyed. My recount from runs/*.json matches the builder on every number. The spend was about $0.60 on 1 rental, and vast credit is now about $5.

| mark | seed 1 | seed 2 |
|---|---|---|
| P296b.1 invented after the fact-check (fresh, transfer) | 0, 0 PASS | 0, 0 PASS |
| P296b.2 diagnosis counts 1–7 / comparing (bar 160 each) | 200 / 93: FAIL | 200 / 88: FAIL |
| P296b.3 fresh counting+comparing (bar 40) | 42 PASS | 45 PASS |
| P296b.4 fresh total (bar 228) | 226 FAIL | 230 PASS |
| P296b.5 code-doable (168) / transfer (228) | 170 / 261 PASS | 170 / 255 PASS |

## What it shows
- **Shown: being told the answer after a miss teaches counting.**
  - Counts 1–7 went from fixed picks in 296 to 200/200 on both seeds.
  - The fresh panel's counting went from 12/30 in 296 to 29/30.
  - Transfer went from 238 to 261 and 255.
  - Counts 8–12 are still 0/200. They were never practised: the model only counts inside the range it was taught.
  - The 30M net can count, so the tiny CPU check was misleading.
- **Shown: comparing is not learned even when told the answer.** It scored 93 and 88 of 200, which is chance, and 13 and 16 of 30 on the fresh panel.
  - Suggested cause (untested): the answer is a "first person / second person" slot read from one summary token. The model must link each named person to their number row and then compare. The number is only a rank among all the notebook's numbers.
  - This is an architecture/encoding problem, not a practice problem.
- **Shown: before/after got worse.**
  - Generated episodes: seed 1 went from 265 to 234 of 400, and seed 2 from 291 to 173.
  - Fresh panel: seed 1 went from 24 to 14, and seed 2 from 20 to 15.
  - The cause isn't known yet (untested). A lead: the told answer for before/after also trains the cited-fact bits on both dated rows.
- Three-step is still 0 (never practised).

The 296 line has used its one follow-up. Any compare-readout change is a new registered number.
