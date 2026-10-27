# rsn-351 verification (sleep research thread, 2026-09-25 01:55 UTC)

**rsn-351 = registered FAIL.** The 3x model (91.6M) at learning rate 1e-4 did not beat the 30M model.

Checked:
- Code seal: SEAL-code.sha256.txt 6/6 OK on main. The builder's commands used `--lr 1e-4` (run log).
  Run seal: 4 checkpoints on the Mac, not re-hashed here.
- My recount from by_category in the panel JSONs on builder-outbox matches RESULTS.md exactly.
- Blind second recount (an Opus agent that did not see RESULTS.md or the builder's verdict): same counts,
  same verdict, "proved wrong" clause not triggered.

| mark | bar | s1 | s2 |
|---|---|---|---|
| Y1 fresh total vs 30M | ≥235 / ≥227 | 221 FAIL (30M: 225) | 218 FAIL (30M: 217) |
| Y2 fresh total vs rsn-350 | ≥221 / ≥219 | 221 PASS (on the line) | 218 FAIL (1 short) |
| Y3 three-step, never practised | ≥6/30, one seed | 0 | 0 |
| Y4 invented (checked) | ≤2 each panel | 0 / 0 PASS | 0 / 0 PASS |

Transfer panel294: 234 / 237 (30M: 238 / 238). Spend $0.70 (guard: $0.65, 3 boxes, 2 died early).

Where the 3x loses its lead (my comparison, from the copy-only checkpoints):

| fresh panel296 total | s1 3x | s1 30M | s2 3x | s2 30M |
|---|---|---|---|---|
| after the copy phase | 183 | 167 | 182 | 181 |
| after practice (RL) | 221 | 225 | 218 | 217 |

- Shown: after the copy phase the 3x is ahead (+16 and +1). During practice the 30M gains more (+58/+36
  vs +38/+36), and ends ahead on s1. Practice reward plateaus at ~0.89 (30M: 0.93 / 0.98).
- Shown: the slower rate helped the 3x over rsn-350 (+10 / +9; counting 12 and 11 of 30 vs 4).
- Not settled: whether the fast rate explains 350's drop (one seed exactly on the line, one seed 1 short).
  Scored on raw answers instead of checked ones, Y2 would fail on both seeds (217 / 213).
- Caveat (plan 352): the 30M was not rerun at 1e-4 (Ben held 351b), so the two sizes did not get equal
  tuning. That caveat only matters for a win; this is a FAIL either way.
- Three-step stays 0/30 at every size so far: this is not a size problem.
