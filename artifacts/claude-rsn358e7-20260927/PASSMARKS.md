# rsn-358e7 pass marks: do lateral connections let the grown experts learn the new kind? (fixed before any run; sleep research thread, 2026-09-27T18:46:05Z)

**Why:** Ben 18:42 UTC: "What if we did something where the neural net just gets bigger? We freeze the neurons, and add a new neuron each sleep?" Ben 18:44 UTC: "can you do that now?" (both relayed by the Thread manager, who asked for this test). In rsn-358e3 (RESULTS.md), freeze + grow + replay kept grids (191 / 188) but the new experts learned sums badly (136 / 67), and the report-only dense-replay learned sums fully (200 / 200).

**Code:** scripts/claude_rsn358e7_lateral.py. It imports claude_rsn358e3_replay.py, claude_rsn358e2_arms.py and claude_rsn358e_moe.py unchanged. CPU, 1 thread per run, small nets, seeds 1-2, the same steps (2,500 / 2,500 / 1,500), data, dev sets (seed 48000), replay (every 10th phase-B step is a grids batch from the phase-A pool, 250 batches) and scoring (own stop, 48 rounds) as rsn-358e3.

**The one change** (graded arm moe-grow-lat-replay vs 358e3's moe-grow-replay): lateral connections, as in Progressive Neural Networks (Rusu et al. 2016). Each new expert also reads the frozen old experts. On every cell it is sent, the sum of all older experts' outputs passes through a new matrix U (d -> hidden, zero at the start) and is added inside the new expert before its GELU. At the start of phase B the net is exactly moe-grow-replay (the selftest checks this). Old weights stay frozen.

| arm | role | total weights in B | trainable in B |
|---|---|---|---|
| **moe-grow-lat-replay** | **graded** | 3,229,358 | 1,579,016 |
| moe-grow-replay (358e3, seeds 1-2, already run) | the reference | 2,705,070 | 1,054,728 |
| dense-big-replay | report only, the size control: MLP hidden 2,567, all trainable | 3,229,868 | 3,229,868 |

## Marks (dev, right of 200, the net's own stop)
- **V:** grids5 after A >= 120 on both seeds. Phase A is unchanged, so this should be 187 / 188 exactly. Otherwise INCONCLUSIVE.
- **PASS:** grids5 after B >= 150 on both seeds AND sums4 after B >= 150 on both seeds.
- **Proved wrong** ("lateral connections let the frozen, grown net learn the new kind"): sums4 after B <= the reference + 10 on both seeds, that is <= 146 on seed 1 and <= 77 on seed 2.
- Anything else is a FAIL, not proved wrong.
- **Size claim, fixed now:** "the growing net learns as well as a dense net of its size" only if, on both seeds, moe-grow-lat-replay >= dense-big-replay on grids5 after B AND on sums4 after B. Otherwise no such claim; the rows are reported.

## Report only
- Every arm: grids5, grids6, sums4, sums6 and maze7 after each phase.
- F = grids5 after A − grids5 after B; expert shares.
- Total and trainable weights per phase; replayed_batches (must be 250); minutes.

**Prediction:** PASS 20%; proved wrong 45%. The old experts learned grids, so their outputs may carry little that helps sums. The attention, embeddings and head also stay frozen, and laterals do not free them.
**Cost:** $0, CPU in this container. 4 runs at once. rsn-358k's 4 CPU runs are paused (SIGSTOP by exact PID) while these run, and resumed after (SIGCONT); its cap is wall-clock, 20 h, with room.
