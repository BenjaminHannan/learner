# rsn-358e3 pass marks: does a small grids replay stop the grown router forgetting? (fixed before any run; sleep research thread, 2026-09-26 21:59 UTC)

**Why:** rsn-358e stage 1 FAILED (artifacts/claude-rsn358e-20260926/RESULTS.md, 91ac1343a). Its diagnostic (DIAG-moe-grow.md, 4aedbf9ea) showed the frozen old experts still held all of grids (187 / 188 with old-only routing). The loss came from the grown router, trained on sums only, sending grids cells to the new experts. Draft: NEXT-replay-draft.md (2b811d47c), settled with the Thread manager 20:27-21:58 UTC.
**Brain angle:** interleaved replay (complementary learning systems). That it helps networks is established; for this router it is untested.

**Code:** scripts/claude_rsn358e3_replay.py (8ba72fe39), importing claude_rsn358e_moe.py and claude_rsn358e2_arms.py unchanged. CPU, 1 thread, seeds 1-2, small nets, the same steps (2,500 / 2,500 / 1,500), data, dev sets (seed 48000) and scoring as rsn-358e.
**The one change (graded arm moe-grow-replay vs rsn-358e's moe-grow):** in phase B, steps 10, 20, ..., 2,500 (250 batches, fixed now) use a grids batch from the phase-A grids training pool, never a dev set, instead of a sums batch. result.json records the count ("replayed_batches", must be 250).

| arm | role | total weights in B | trainable in B |
|---|---|---|---|
| **moe-grow-replay** | **graded** (not same-size: 1.64x dense, as moe-grow) | 2,705,070 | 1,054,728 |
| moe-grow-eq | report only (same-size layout, no replay) | 1,654,446 | 352,944 |
| moe-grow-eq-replay | report only | 1,654,446 | 352,944 |
| dense-replay | report only (the fair control) | 1,646,750 | 1,646,750 |

## Marks (dev, right of 200, the net's own stop)
- **V:** grids5 after A >= 120 on both seeds for moe-grow-replay. Phase A is unchanged from moe-grow, so this is expected to be 187 / 188 exactly. Otherwise INCONCLUSIVE.
- **PASS:** grids5 after B >= 150 on both seeds AND sums4 after B >= 120 on both seeds.
- **Proved wrong:** grids5 after B <= 100 on both seeds.
- Anything else is a FAIL, not proved wrong.
- **Split readings, fixed now:**
  - grids5 >= 150 on both seeds with sums4 < 120 on a seed: FAIL, read as "replay keeps the old skill; the frozen net's capacity, not replay, is the sums problem".
  - grids5 < 150 on a seed: replay did not fix the router.
- **No experts-vs-dense claim** comes from this test. The Thread manager's question "do experts help beyond replay" is deferred to a same-size test, and only if replay is shown to work here.

## Report only
- Every arm: grids5/grids6/sums4/sums6/maze7 after each phase; F = grids5 after A - after B; expert_share and S after B; trainable counts as in the table.
- moe-grow-eq: expected in advance (NOTE-moe-grow-eq-caveat.md) to score below 187 / 188 after A, since its phase-A MLP is a third as wide. Its after-A score is a report row. A low sums4 after B there is expected from its 352,944 trainable weights and is not a finding about replay.
- dense-replay: whether replay alone keeps grids in the dense loop.

**Prediction:** PASS 35%. Replay should keep most of grids5, but it takes 10% of phase-B steps from sums, and moe-grow's sums4 was already only 139 / 124.
**Cost:** $0, CPU. 8 runs, 4 at a time after moe-aux0 and dense-narrow finish.
