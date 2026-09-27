# rsn-358e4 addendum 1 (2026-09-27 00:35 UTC, before any run; replaces the marks in PASSMARKS.md where they differ)

**Why:** the Thread manager's review at 00:34 UTC, points 1-8. I sealed at 00:28 without sending the marks first, which was my slip. No 358e4 run has started; both launchers were stopped by exact PID at 00:35 UTC.

**1. What is compared.** This is a **freeze-and-grow package vs a dense loop, at equal total weights**. It is not "experts vs dense". eq_grow freezes everything trained so far: old experts, attention, embeddings, norms, the stop head and old router rows (claude_rsn358e3_replay.py:64-76). Only the new router group and its 4 experts train.

| phase | eq-replayall trainable | dense-replayall trainable |
|---|---|---|
| A | 948,558 | 1,646,750 |
| B | 352,944 (21%) | 1,646,750 |
| C | 352,944 (21%) | 1,646,750 |

Total weights: 1,654,446 vs 1,646,750.

**2-3. Marks, replacing PASSMARKS.md's.** Seeds 3-8 (6 seeds, up from 4). T = grids5 + sums4 + maze7 after C (of 600); L = maze7 after C.
- **V (unchanged):** on every seed, grids5 after A >= 120 in both arms, and sums4 after B >= 120 in dense-replayall. Otherwise INCONCLUSIVE.
- **PASS:** all three of these:
  - mean T_eq >= mean T_dense + 40;
  - T_eq > T_dense on >= 5 of 6 seeds;
  - mean L_eq >= 100 (a learning floor, so T cannot pass with mazes near 0).
- **Proved wrong:** mean T_eq <= mean T_dense - 40 AND T_eq < T_dense on >= 5 of 6 seeds. This is the same shape as PASS.
- Anything else, with V met, is a FAIL, not proved wrong.
- Bar size: 358e3's two seeds differed by 69 on sums4 alone. So the bar is raised from 30 to 40 and the seeds from 4 to 6. Whether 40 on 6 seeds clears the noise is still suggested, not shown.
- Predictions: PASS 10%; proved wrong 55%.

**4. Half-replay arms, sealed now as report only:** scripts/claude_rsn358e4b_halfreplay.py, the same two arms with 1 step in 20, seeds 3-4 only. Nothing is ever graded from them.

**5. Meaning of outcomes, corrected:**
- Proved wrong: "at equal size with full replay, the freeze-and-grow package keeps and learns less than the dense loop". Whether to go on with separate experts in the reasoner is **a question for Ben**, not my call.
- PASS: also a question for Ben (architecture), with a recommendation.

**6. Bug fixed before any run:** the after-B "replayed" field was a shallow copy, so it would have shown phase-C counts too. It is now a per-phase snapshot (claude_rsn358e4_replayall.py:60). Training is unchanged; the selftests pass. The "replayed_batches: 0" field that 358e3's hook writes (claude_rsn358e3_replay.py:119-120) is unused here.

**7. Not a held-out test:** the dev sets (seed 48000) were already read in 358e and 358e3. This is a dev-set comparison, stated as such.

**8.** Struck from PASSMARKS.md: "which is itself a capacity finding". An INCONCLUSIVE result is not a finding.

**Run order after the Thread manager has read this:**
- batch 1: seeds 3-4, both arms;
- batch 2: seeds 5-6;
- batch 3: seeds 7-8;
- batch 4: half replay, seeds 3-4.
Each batch is 4 runs at a time on CPU, about 1.5 h (estimate), and $0. Each batch start gets a run note.
