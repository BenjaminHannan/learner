# rsn-358k RESULTS: PROVED WRONG (written 2026-09-28T20:34:20Z)

Sealed marks: PASSMARKS.md with PASSMARKS-draft-2.md (V, G1, G1k, G2, G3). 8,000 steps (PILOT-RESULT.md). CPU in this container; the 4 graded store/no-store pairs (s17-s20) and the report-only pasted arm (s17-s18) finished 06:35 UTC 09-28 (runs/drive-state.txt; each run committed as it finished). Four runs were paused 18:49-21:31 UTC 09-27 (SIGSTOP/SIGCONT by exact PID) while rsn-358e7 ran; that changes wall time only. A blind recount by a fresh worker from tests.json and the marks only agrees.

| seed | store q1 | store q1 card chosen at round 1 (G1k) | store q2 | store q2 at fixed round 1 | no-store q1 | no-store q2 |
|---|---|---|---|---|---|---|
| 17 | 24 | 24 | 41 | 36 | 0 | 0 |
| 18 | 6 | 0 | 8 | 8 | 6 | 8 |
| 19 | 26 | 27 | 36 | 34 | 0 | 0 |
| 20 | 21 | 19 | 29 | 28 | 5 | 2 |
| mean | 19.25 | 17.5 | 28.5 | 26.5 | | |

- **V:** met (no-store <= 15 on q1 and q2, every seed).
- G1 (q1 mean >= 240): not met. G1k (mean >= 200): not met. G2 (q2 mean >= 150): not met. G3 (own stop >= fixed 1 round + 50): not met (+2.0).
- **Proved wrong** (V met and G1k mean <= 100): **fired**, 17.5 of 300.
- Report only, pasted arm (s17 / s18): q1 13 / 14, q2 26 / 27.
- Seed 18's store net scores exactly what its no-store net scores (6 / 8): it learned to use no stored card at all. The pilot already showed the store arm barely learning (PILOT-RESULT.md: "the pilot never flattened").
