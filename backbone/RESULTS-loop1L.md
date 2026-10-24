# Loop-1L results (PREREG-loop1L.md + addenda 1-2)

Box 57514215 (A100 80GB, France), 2 h cap. Run order was seed-major, so only seed 0 of every arm plus seed 1 of arm A finished.
Spend: about $2.0 for this box plus about $0.7 on the two failed starts, so about $2.7 of the $3 approval.

## Main metric (M_tool on 100 eval chats, 322 turns)

| arm | seed | laps at test | M_tool | tool turns | no-tool turns | eval loss |
|---|---|---|---|---|---|---|
| A (LoRA, no loop) | 0 | 1 | **48.8** | 23.4 | 82.6 | 0.589 |
| A | 1 | 1 | **46.6** | 19.6 | 82.6 | 0.585 |
| B (layers 16-23 looped) | 0 | 8 | 40.1 | 14.7 | 73.9 | 0.796 |
| C (B + latent board) | 0 | 8 | 42.9 | **0.0** | 100.0 | **7.33** |

## Lap curve (same 50 extra chats)

| arm | 1 lap | 4 laps | 8 laps | 12 laps |
|---|---|---|---|---|
| B | 41.4 | 43.8 | 40.7 | 29.6 |
| C | 42.0 | 7.4 | 42.0 | 42.0 (board zeroed: 0.0) |

## Verdict against the pass marks

- K1 (B >= A+2 in 3 of 4 seeds): **fail**. B seed 0 is 7.6 points below the mean of A (47.7).
- K2 (C >= B+2): **not valid**. Arm C diverged: eval loss 7.3 and it never makes a tool call. Its 42.9 comes only from turns where the right move is to answer without a tool. This is a broken run, not evidence about the board.
- K3 (tau2): not run. No loop arm beat A, so Phase 2 has nothing to test.
- Prereg "wrong if" (B and C both <= A): **met for this setup**, with the caveats below.

## What it shows / suggests / leaves untested

- Shown (1 seed): looping layers 16-23 with random 1-8 laps, trained on 448 chats for 56 steps, makes the model worse than plain LoRA (40 vs 48), even when tested at 1 lap (41).
- Shown (1 seed): more laps do not help at test time. 4 laps is best, and 12 laps (more than training ever saw) drops to 30.
- Suggested: 56 steps is too little for the network to adapt to its own looped output. Re-running layers 16-23 feeds them inputs they were never trained on, and the LoRA cannot repair that in this budget.
- Suggested: the board (lr 1e-3, applied to all positions) blew up training. It needs a zero-init gate and a lower lr. Ben's trained-block design (separate thread) already plans a zero-init gate.
- Untested: longer training, a small loop range (2-4 laps), looping fewer layers, other seeds of B and C.

Raw files: backbone/results/loop1l/.
