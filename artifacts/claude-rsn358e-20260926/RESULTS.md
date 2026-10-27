# rsn-358e results, stage 1 (small nets, CPU, $0): does a mixture-of-experts loop keep an old skill? (sleep research thread, 2026-09-26 21:56 UTC)

## Verdict: FAIL, not proved wrong (moe-grow, the one graded arm, per ADDENDUM-2)
moe-grow forgot much less grids than dense, but it failed the "still learns the new skill" clause: sums4 after B was 131.5 against a bar of 180. It was also 1.64x dense's size in phase B (ADDENDUM-3), so even a pass would not have been same-size. **The FAIL stands.**

Counted from runs/{dense,moe,moe-grow}-s{1,2}/result.json. A blind recount by a separate agent, working from the same raw files and the pass marks only, agrees on every number below.

## Marks (dev, right out of 200, the net's own stop)

| | dense s1 / s2 | moe s1 / s2 (report only) | moe-grow s1 / s2 (graded) |
|---|---|---|---|
| grids5 after A | 199 / 198 | 187 / 188 | 187 / 188 |
| grids5 after B | 0 / 0 | 0 / 0 | 40 / 70 |
| **F = forgetting** | 199 / 198, mean 198.5 | 187 / 188, mean 187.5 | 147 / 118, mean 132.5 |
| sums4 after B | 200 / 200 | 200 / 200 | 139 / 124, mean 131.5 |
| total weights in phase B | 1,646,750 | 1,650,342 | 2,705,070 (1.64x) |
| trainable in phase B | 1,646,750 | 1,650,342 | 1,054,728 |

- **V (validity):** met on every arm and seed (grids5 >= 120 after A, sums4 >= 120 after B).
- **moe-grow PASS clauses:**
  - mean F 132.5 <= 168.5 (dense - 30): met;
  - F below dense on both seeds (147 < 199, 118 < 198): met;
  - mean sums4 after B 131.5 >= 180 (dense - 20): **not met**.
  - So: **FAIL**.
- **Proved wrong** needs mean F >= 193.5; it is 132.5, so not proved wrong.
- **moe (report only):** mean F 187.5 misses 168.5. It forgets nearly everything, like dense, and falls in ADDENDUM-1's middle band.

## Report-only rows
- **Separation S after B** (ADDENDUM-1; block 0, block 1):
  - moe: 0.239, 0.378 and 0.215, 0.146. Grids and sums share experts.
  - moe-grow: result.json gives 0.779, 0.742 and 0.131, 0.526. Those shares were read after the second grow step, with 4 extra zero-initialised experts present. Read on the saved once-grown after-B net (DIAG checkpoints), they are 0.794, 0.730 and 0.156, 0.475. "Different experts" (both blocks >= 0.5) holds on seed 1 only.
  - On that net, 42-59% of grids5 cells go to the new experts.
- **Phase C (mazes, a kind no net had seen):**
  - maze7 after C: dense 154 / 149, moe 140 / 155, moe-grow 3 / 3. moe-grow could not learn mazes through new experts alone.
  - After C, dense and moe are at 0 on sums4; moe-grow keeps 79 / 64.
- **Why moe-grow still forgot:** DIAG-moe-grow.md (4aedbf9ea). All 67 old tensors were byte-identical after B, and routing over the old 4 experts only gives back 187 / 188 exactly. The loss is the grown router sending grids cells to the new experts (mainly) and the gate rescale (less).
- result.json's "weights" field for moe-grow reads 1,650,342, the count before growing.
- All runs: CPU, torch 2.14.0, 1 thread each; minutes: dense 144, moe 121, moe-grow 61.
- moe-aux0 and dense-narrow (report only) are still running; their rows are added when they finish.

## What it means (plain words)
- A dense loop that learns sums after grids forgets grids completely: 0 of 200 on both seeds. Splitting the layer into 4 experts with a learned router changes nothing (still 0).
- Freezing the old experts and adding new ones keeps some grids (40 / 70). The old experts still know grids perfectly, but the router, trained on sums only, stops sending grids to them. The frozen net also learned sums much worse (131.5 vs 200 of 200) and mazes not at all, with only the new third of its weights free to learn. That is why it fails.
- Brain reading (a guess): the gate is part of what has to be protected, and in the brain replay during sleep is the usual answer. The next test (NEXT-replay-draft.md, sealed only now that this verdict is registered) adds 1 grids step in 10 during phase B.

## Next
Per ADDENDUM-1/2 and the Thread manager's notes: the replay test (one change: 250 of 2,500 phase-B steps are grids from the phase-A training pool), at equal size in the moe-grow-eq layout if it is run as a graded test. Its marks are in NEXT-replay-draft.md, and the moe-grow-eq caveat is in NOTE-moe-grow-eq-caveat.md. It is $0 on CPU.

## Added 2026-09-26 23:47 UTC: the two report-only arms (ADDENDUM-1); the verdict above is unchanged
Dev counts of 200, seed 1 / seed 2:

| arm | weights | grids5 after A | grids5 after B | F | sums4 after B | maze7 after C | S after B (block 0, 1) |
|---|---|---|---|---|---|---|---|
| moe-aux0 (no balance loss) | 1,650,342 | 186 / 188 | 0 / 0 | 186 / 188 | 200 / 200 | 124 / 148 | 0.031, 0.647 / 0.056, 0.164 |
| dense-narrow (MLP width d) | 858,782 | 194 / 189 | 0 / 0 | 194 / 189 | 200 / 200 | 157 / 170 | none |

- Dropping the load-balance loss does not make the experts separate by kind (S stays low except block 1 on seed 1), and it forgets grids completely, like moe.
- A dense loop with the same active MLP width as moe (about half the total weights) also forgets completely. So forgetting here does not depend on MLP width or on experts. Every net that trains shared weights on sums alone loses all of grids.
