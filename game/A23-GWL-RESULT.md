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

## Result at N = 64,000, seed 200 (8:33 AM ET 10-14; the pre-registered follow-up; code commit be63ed157d, which adds resumable training; the math is unchanged, tested)
Same constants (10 epochs, 2,500 updates, 6.9 h on 4 threads, the box restarted twice before this run and the run was not hit), same 2,000 held-out
views as the 16k runs (kept as is; the new train set drops any view that is in it), a new train list of 64,000 unique views (practice run seed 390).
| | N = 16,000 (seed 200) | N = 64,000 (seed 200) |
|---|---|---|
| Held-out accuracy on S (1,491 views; always `do` = 27.2%) | 41.9% | **62.4%** |
| L-1 gap | +14.8 | **+35.3** |
| held-out accuracy, all 2,000 views | 49.0% | 67.3% |
| training accuracy at the last epoch (running mean) | 0.56 | 0.71 |
| Sealed unlocks a game, sampled T = 1 | 4.88 | **6.50** |
| minus GW-P8 After (4.15), paired 95% | +0.73 (+0.28 to +1.17) | **+2.35 (+1.87 to +2.79)** |
| minus untrained parent at T0 | +1.13 (+0.72 to +1.53) | +2.75 (+2.29 to +3.20) |
| Sealed unlocks a game, top move | 3.91 | 5.89 |
- Per-word accuracy on S: left 58.8%, right 54.8%, up 58.9%, down 54.6%, do 77.3% (16k: 25 to 56%). Most common slips: `right` read as `up` (55 views), `do` as `left`, `down` as `left` or `do`.
- Sealed achievements (% of maps): wood 97, table 96, **wood pickaxe 83**, wood sword 67, stone 40, drink 57, zombie 52, sapling 38, cow 29, plant 31, wake-up 35,
  coal 10, furnace 3, stone pickaxe 2. The labeller itself (8.23): wood pickaxe 98, stone 83, zombie 78. The student has not reached the labeller (6.50 against 8.23).
- Against A22 as written: its marks are defined at N = 16,000 on both seeds and read **no verdict** there. At N = 64,000 seed 200 meets both bars (L-1 +35.3 >= +20; L-2 +2.35 >= +1.0
  with the interval above 0), as a one-seed screen. Seed 201 at N = 64,000 is queued (needed before it can be called a pass on both seeds); the 4,000 and 1,000 runs (L-3) are running.
- Shown: a 3M model with a rank-8 add-on, read through the 17-word scorer, learns a map-to-move rule from labelled views, and the held-out accuracy and sealed play keep rising with
  the number of labels (16k to 64k: +20 points, +1.6 unlocks). Held-out accuracy is still climbing at 10 epochs on both sizes, so these are floors.
- Shown: the reward-driven runs (GW-P8, 87,000 sparse-reward moves, 4.15) are far below a student that saw 64,000 labelled views. What is not shown: that the model can get
  such labels without the hand-written labeller. The labeller is the whole teacher here (it encodes where trees, water and cows are, when to craft); this is a capacity result,
  not a self-teaching result.
- Suggested, untested: size is not the limit at 3M for these basics; the limit is how the model finds good labels by itself. Candidate label sources that need no hand-written
  labeller (all untested): hindsight labels from the model's own unlocks with a longer or smarter window than the 8-move rule of GW-S; search with the game as a tool (copy the world,
  look ahead, label the first move of the best path, then distil: expert iteration); a learned value used to relabel.

## L-3: the label-cost curve, N = 1,000 / 4,000 / 16,000 / 64,000 (11:05 AM ET 10-14; same constants, same 2,000 held-out views, nothing tuned)
Epochs were the fixed A22 numbers (40 / 20 / 10 / 10), so the update counts were 160 / 320 / 630 / 2,500: **label count and update count are confounded**
(more labels means more updates here); this curve says how the fixed recipe scales, not what the labels alone are worth. All **shown**. S = the 1,491
map-dependent held-out views; always `do` = 27.2%. "vs After" = paired 95% interval of sealed unlocks minus GW-P8 After (4.15 / 4.19).
| labelled views | seed | training accuracy, last epoch | S accuracy | L-1 gap | sealed unlocks (sampled, T = 1) | minus GW-P8 After |
|---|---|---|---|---|---|---|
| 1,000 | 200 | 0.66 | 25.8% | -1.4 | 4.18 | +0.03 (-0.40 to +0.45) |
| 1,000 | 201 | 0.59 | 24.5% | -2.7 | 3.50 | -0.69 (-1.02 to -0.35) |
| 4,000 | 200 | 0.52 | 27.7% | +0.5 | 4.42 | +0.27 (-0.14 to +0.71) |
| 4,000 | 201 | 0.46 | 31.3% | +4.2 | 3.47 | -0.72 (-1.09 to -0.34) |
| 16,000 | 200 | 0.56 | 41.9% | +14.8 | 4.88 | +0.73 (+0.28 to +1.17) |
| 16,000 | 201 | 0.54 | 45.4% | +18.3 | 4.62 | +0.43 (+0.04 to +0.82) |
| 64,000 | 200 | 0.71 | 62.4% | +35.3 | 6.50 | +2.35 (+1.87 to +2.79) |
| 64,000 | 201 | queued (running) | | | | |

- Shown: with 1,000 labels the student memorises its labelled views (training accuracy 0.59 to 0.66) and reads the map no better than the fixed word (S 24.5 to 25.8%,
  below 27.2%); sealed play is at the reward-trained level (3.5 / 4.18, parent T0 about 3.6-3.8) or below it. At 4,000 labels held-out S accuracy is still within
  +0.5 to +4.2 points of the fixed word (L-1 would read "proved wrong" for 4k: < +5 on both seeds). The map-reading gain appears between 4,000 and 16,000 labelled views
  and keeps rising to 64,000 (seed 200). L-3 (smallest N where +20 holds) is therefore **somewhere in 16,000 to 64,000 on seed 200 only**; 64,000 is the only size tested above
  +20, and no size between 16,000 and 64,000 was run.
- Shown: with 1,000 and 4,000 labels the sealed score is not above the reward-trained runs on either seed (the 4k seed 200 interval includes 0), so with this recipe a few thousand
  labels do not beat the sparse reward, and tens of thousands do. (Suggested, untested: a label budget a person could write by hand would not be enough for this recipe.)
- Suggested, untested: the 1k and 4k runs are short (160 and 320 updates) and the first epochs show an unstable loss (loss 45 to 3 in the first ten epochs of 1k), so some of the
  4k/1k deficit is the fixed recipe (lr 1e-3, no warm-up) and the small step count, not the label count. A run at 4,000 labels with the 16k run's update count would separate the two
  (not scheduled; it would be a new design, with marks fixed first).
- Not shown: why the 1,000-label student ends below the fixed word on S (memorisation of 1,000 views is the obvious reading; the per-word table shows `do` 47% on seed 200 against 33% on seed 201,
  so the two seeds fall into different habits).
