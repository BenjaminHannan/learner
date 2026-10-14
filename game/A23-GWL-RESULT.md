# A23 (11:58 PM ET 10-13): GW-L at 16,000 labels, both seeds (first part of the result; 4k, 1k and the 64k follow-up are added below as they land)

Written after the numbers below existed; the marks are A22 (commit d7800df0aa, 7:56 PM ET 10-13), fixed before any run. Code: commit a3e57da490
(labeller, probe, score oracle arm); data, checkpoints and scores in the cloud scratchpad (`glprobe/run/`). All **shown** unless marked.
Run notes: gen 5 min, N = 16,000 training 2.6 h for the pair (630 updates each, 10 epochs, 2 threads each), eval 4 min, sealed scoring 15 min a sample
arm. The box restarted right after training; the pipeline is idempotent and was relaunched from the eval step. Training accuracy was still rising at
the last epoch (running mean per epoch, seed 200: 0.18, 0.28, 0.34, 0.39, 0.42, 0.48, 0.51, 0.53, 0.55, 0.56; seed 201: 0.21 .. 0.54), so these
students are not converged. The epochs are the fixed A22 numbers; nothing was tuned.

## Labeller ceiling (sealed maps, same act rule)
The labeller itself, explore 0.10: 8.23 unlocks a game (wood 100%, table 100%, wood pickaxe 98%, wood sword 91%, stone 83%, drink 78%, zombie 78%,
cow 70%, furnace 31%, stone pickaxe 7%). Random 2.31; GW-P8 After 4.15 / 4.19.

## Marks
| | seed 200 | seed 201 |
|---|---|---|
| Held-out accuracy, map-dependent views S (1,491 views): student | 41.9% | 45.4% |
| best fixed word on S (always `do`) | 27.2% | 27.2% |
| L-1 gap (bar +20 pass, < +5 proved wrong) | **+14.8** | **+18.3** |
| untrained parent / GW-P8 night-8 on S | 27.0% / 27.2% | 27.0% / 27.1% |
| held-out accuracy, all 2,000 views (fixed word 20.3%) | 49.0% | 51.7% |
| Sealed unlocks a game, sampled T = 1 (L-2) | 4.88 | 4.62 |
| minus GW-P8 After (4.15 / 4.19), paired 95% | **+0.73 (+0.28 to +1.17)** | **+0.43 (+0.04 to +0.82)** |
| minus untrained parent at T0 | +1.13 (+0.72 to +1.53) | +1.01 (+0.60 to +1.42) |
| Sealed unlocks a game, top move (reported) | 3.91 | 3.60 |

- **L-1: no verdict** (between +5 and +20 on both seeds). **L-2: no verdict** (between +0.3 and +1.0 on both seeds; both intervals are above 0).
- Reading (shown): the model is not blind to the map. On views where the right move depends on the map it is 15 to 18 points above the best
  fixed word; the untrained parent and GW-P8's final policy are at the fixed word's level (27%), i.e. they do not read the view in this sense.
- Achievements on sealed maps (student 200 / 201 vs GW-P8 After 200 / 201): wood 97 / 97 vs 52 / 59; table 89 / 89 vs 18 / 22; **wood pickaxe 44 / 20
  vs 3 / 2**; wood sword 21 / 28 vs 3 / 2; stone 15 / 7 vs 0 / 0; zombie 17 / 25 vs 11 / 9; drink 52 / 55 vs 38 / 34. It loses the habit
  achievements: sapling 55 / 63 vs 98 / 100, plant 31 / 21 vs 86 / 92, wake-up 45 / 42 vs 91 / 89. The labeller does not collect saplings either.
  The wood-pickaxe share is the first above the 10% bar (GW2 / P-3 / Q-3 style) of any trained arm in this thread (this one is supervised).
- Most common slips on S: seed 200 mixes the four moves among themselves and with `do` (`right` read as `up`, `up` as `down`), seed 201 says `do` for a move
  (`left`, `up`, `down`, `right` each 70 to 84 times).

## What it means (suggested, untested)
- The 3M model with a rank-8 add-on and the 17-word scorer can hold a map-to-move rule; the limit is not a wall. With 16,000 labelled views
  (GW-P8 saw about 87,000 sparse-reward moves) it already plays above every reward-trained run.
- So the reward-driven runs probably stalled on the signal, not on size. Counter-reading to keep in mind: the labeller's labels contain
  navigation the reward runs never see in one place; part of the 16k students' play comes from what the labeller does in 50% of the recorded
  steps (it teaches the right habit, not only reading). The held-out accuracy gap above the fixed word is the cleaner reading of map reading.
- Not shown: that the model reaches the labeller; the gap (4.9 vs 8.2 unlocks) is open, and the top-move play is worse than the sampled
  play, so the student is not yet decisive.

## Pre-registered next (A22 "anything between")
One run at N = 64,000 on seed 200 (10 epochs, the same constants), with the same held-out views. The smaller label counts (4,000 and 1,000)
are running first and give the label-cost curve (L-3).
