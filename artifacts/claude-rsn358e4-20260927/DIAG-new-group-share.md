# rsn-358e4 diagnostic: does the new router group get the new kind? (report only; written 2026-09-27 02:48:50 UTC)

Asked by the Thread manager at 02:46 UTC. **No mark depends on this.** It reads only result.json and log.jsonl files already on main: 358e4 seeds 3-4, and 358e3's four freeze-and-grow runs. Seeds 5-8 are not read here.

**Measure.** expert_share is the share of cells that top-1 routing sends to each expert, on the first 100 dev items at round 8 (claude_rsn358e_moe.py:124-133). "New group" means experts 4-7 for phase B and experts 8-11 for phase C. Each cell holds two numbers, one per block.

| run | new group's share of sums4 after B | new group's share of maze7 after C | sums4 after B | maze7 after C |
|---|---|---|---|---|
| 358e4 eq-replayall s3 | 0.735, 0.787 | 1.000, 0.121 | 75 | 7 |
| 358e4 eq-replayall s4 | **0.000, 0.000** | 0.694, 0.694 | 0 | 0 |
| 358e3 moe-grow-eq-replay s1 | 0.667, 0.667 | 0.000, 0.000 | 0 | 0 |
| 358e3 moe-grow-eq-replay s2 | 0.536, 0.827 | 0.306, 0.041 | 59 | 8 |
| 358e3 moe-grow-eq s1 | 1.000, 0.703 | 0.020, 0.020 | 53 | 3 |
| 358e3 moe-grow-eq s2 | 0.756, 0.833 | 0.306, 0.020 | 94 | 2 |
| 358e3 moe-grow-replay s1 (1.64x, wide experts) | 0.944, 0.876 | 0.940, 0.598 | 136 | 9 |
| 358e3 moe-grow-replay s2 (1.64x, wide experts) | 0.667, 0.910 | 0.306, 0.694 | 67 | 0 |

What this shows and suggests:
- **Shown: in eq-replayall s4, the new group got none of the sums cells in either block.** Its after-B sums4 share row is identical to the one read after phase A. With top-1 routing only the chosen expert gets a gradient, so experts 4-7 could not learn sums. The Thread manager's reading is right for this seed.
- **Shown: in 7 of the 8 freeze-and-grow runs above, the new group got at least half of the new kind's cells in at least one block after B.** Even so, sums4 stayed at 0-94 at equal size. The one exception is eq-replayall s4.
- **Suggested: in most runs, a starved router is not the whole cause.** eq-replayall s3 sent 74-79% of sums cells to the new group and still reached only 75. Mazes are routed to the new group in several runs (s3 block 1: 1.000; s4: 0.694 in both blocks) and are still near 0. At equal size the new experts are 85 wide, with attention, embeddings and the stop head frozen. The 1.64x arm (256-wide experts) learned more sums with similar routing. That points to capacity, but it is untested.
- The dead-group case (s4) is real, and warm routing would address it (see NEXT-358e5-draft.md). The data above say it would probably not be enough alone.

**Loss "spikes" are replay batches, not instability.** Every logged step (each 250th) is a multiple of 10, so every logged phase-B and phase-C loss is a replay batch. In phase B these are grids. In phase C, steps 250, 750 and 1250 are sums and steps 500, 1000 and 1500 are grids (claude_rsn358e4_replayall.py:37-41). eq-replayall s4 logs 4.99, 4.46 and 4.34 at maze steps 250, 750 and 1250. Those are sums batches for a net whose sums4 is 0. Its grids batches at 500, 1000 and 1500 log 0.41, 0.12 and 0.10. The logs therefore never show the new kind's training loss, in 358e3 or in 358e4. This is disclosed as a gap in the logging, not a fault in training.

**Correction to 358e3 RESULTS.md (the eq-arm section added at ffa9be16d).** It says S "was read before the second grow step". That is wrong. X.run reads expert_share after score() (claude_rsn358e_moe.py:178-179), and the eq arms grow inside score() (claude_rsn358e3_replay.py:117-118). So every eq after-A share was read after the first grow, and every after-B share after the second. The newly added group is zero-initialised, so it wins only on cells where every trained logit is below 0. In these runs it got 0.000-0.002 of the cells at those reads, so the shares above are affected by at most 0.002. The same holds for the 358e4 eq runs.
