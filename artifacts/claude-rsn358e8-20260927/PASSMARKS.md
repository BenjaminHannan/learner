# rsn-358e8 pass marks: can a frozen dense net learn a new kind if each layer only grows new units? (fixed before any run; sleep research thread, 2026-09-27T18:58:28Z)

**Why:** Ben 18:54 UTC: "I meant what if we have a dense model, and then each sleep, each layer gets one new neuron" (relayed by the Thread manager, who asked for this test: base 358e3 dense-replay, one change, a k=1 arm and a larger-growth arm, a same-size dense control, seeds 1-2, $0 CPU). Earlier, Ben 18:42: "We freeze the neurons, and add a new neuron each sleep". rsn-358e7 (lateral experts) is a separate test and runs first.

**Code:** scripts/claude_rsn358e8_growunits.py. It imports claude_rsn358e3_replay.py and claude_rsn358e_moe.py unchanged. CPU, 1 thread per run, small nets (2 x d256 loop), seeds 1-2, the same steps (2,500 / 2,500 / 1,500), data, dev sets (seed 48000), replay (every 10th phase-B step is a grids batch from the phase-A pool, 250 batches) and scoring (own stop, 48 rounds) as rsn-358e3.

**The one change** (vs 358e3's dense-replay): at the end of phase A and again at the end of phase B, every weight already trained is frozen and each block's MLP gets k new hidden units, which are the only trainable weights in the next phase. A new unit reads the whole residual stream (d + 1 weights in) and writes back into it (d weights out, zero at the start, so the grown net starts each phase exactly as the last one ended; the selftest checks this and that frozen weights do not move). Phase A is the plain dense net, as in dense-replay.

Disclosed: only the MLP grows. Attention, embeddings, norms, the answer head and the stop head do not grow and stay frozen after phase A. Old skills can still shift through the new units' outputs; replay is what guards against that. "One neuron per layer" is read as one new MLP hidden unit per block per phase (a "sleep" here is a phase change; 2 blocks, so k = 1 adds 1,026 weights).

| arm | role | total weights in B | trainable in B |
|---|---|---|---|
| **grow1-replay** | **graded**: Ben's literal k = 1 | 1,647,776 | 1,026 |
| **grow1024-replay** | **graded**: k = 1,024 (MLP hidden doubles in B) | 2,697,374 | 1,050,624 |
| dense-replay (358e3, seeds 1-2, already run) | size control for grow1 (1,646,750, all trainable) | 1,646,750 | 1,646,750 |
| dense2048-replay | report only, size control for grow1024: MLP hidden 2,048 from the start, all trainable | 2,697,374 | 2,697,374 |

## Marks, per graded arm (dev, right of 200, the net's own stop)
- **V:** grids5 after A >= 120 on both seeds. Phase A is dense-replay's, so this should be 199 / 198. Otherwise INCONCLUSIVE.
- **PASS:** grids5 after B >= 150 on both seeds AND sums4 after B >= 150 on both seeds.
- **Proved wrong** ("growing new units on a frozen dense net lets it learn the new kind"): sums4 after B <= 40 on both seeds.
- Anything else is a FAIL, not proved wrong.
- **Size claim, fixed now:** "the growing net learns as well as a dense net of its size" only if, on both seeds, the grown arm >= its same-size dense control on grids5 after B AND on sums4 after B (grow1 vs 358e3 dense-replay: grids5 184 / 172, sums4 200 / 200; grow1024 vs dense2048-replay). Otherwise no such claim; the rows are reported.

## Report only
- Every arm: grids5, grids6, sums4, sums6 and maze7 after each phase; grids5 after C.
- F = grids5 after A - grids5 after B.
- Total and trainable weights per phase; replayed_batches (must be 250); minutes.

**Prediction:** grow1: PASS 2%, proved wrong 90% (1,026 free weights, attention and head frozen). grow1024: PASS 25%, proved wrong 20% (358e3's frozen experts with about as many free weights reached 136 / 67; here the new units see every old feature, but attention and the head stay frozen).
**Cost:** $0, CPU in this container, 1 thread per run, at most 4 runs at once. They start after rsn-358e7's 4 runs end, so 358e7 is not slowed. rsn-358k's 4 CPU runs stay paused (SIGSTOP by exact PID) until 358e8 ends, then resume (SIGCONT); its cap is wall-clock, 20 h.
