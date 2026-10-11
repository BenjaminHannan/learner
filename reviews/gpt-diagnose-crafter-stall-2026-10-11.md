# Outside opinion: why does a small text model stall at about 3.3 goals a game in Crafter?

You cannot see our code, so everything you need is below. Please label every claim **shown** (follows from the numbers here),
**suggested** (likely, not checked) or **untested**. Treat this game test on its own; do not mix it with other experiments of ours.

## The setup
- Game: Crafter 1.8.3 (Hafner 2021), 22 achievements, 17 actions, a new random map every game, game ends at death or 1,000 steps.
  Random play gets about 2.3 of 22 achievements a game.
- The model sees Crafter as text: a 9x7 letter map around the player, health/food/drink/energy, a sleeping and darkness mark, and the
  inventory (at most 108 letters). It answers one move word (17 words such as `do`, `up`, `table`, `wpick`), decoded letter by letter
  (greedy). With 10% chance, or when the answer is not one of the 17 words, the game takes a uniformly random move instead.
- The model: a 3M-parameter text reasoner pretrained on puzzles and arithmetic, never on games. Before any game practice it writes
  no valid move word at all, so its "Before" play is pure random.
- The self-teaching loop, per "day": play 64 new practice maps; for every achievement unlocked for the first time in a game, keep
  the 8 moves (view, move taken) just before the unlock, whatever produced the move (the model, the 10% random rule or the invalid
  fallback). At "night", train a small add-on (rank-8 adapter) on the kept rows, about 16 passes each; a check guards old skills;
  a 32-map quiz decides when to stop (stop when the quiz rose less than 1 point over 2 nights).
- Scoring: 100 sealed maps never used in practice, achievements unlocked per game, paired by map.

## Results (three runs; numbers are achievements unlocked per game on the sealed maps)
| run | nights | Before | After | After - Before (95% interval) |
|---|---|---|---|---|
| seed 200, add-on | 4 | 2.21 | 3.50 | +1.29 (0.94 to 1.65) |
| seed 201, add-on | 3 | 2.21 | 3.32 | +1.11 (0.82 to 1.41) |
| seed 200, whole model trained (no add-on) | 4 (3 undone by the old-skills check) | 2.21 | 3.28 | +1.07 (0.76 to 1.39) |
A plain PPO agent (2x256 MLP on a one-hot of the same text view, CleanRL defaults) given the same number of game moves gets 2.38-2.39;
at 3x the moves 2.51. Our bar was +1.5 and a wood pickaxe on 10% of maps: no run made any wood pickaxe on the sealed maps.

Achievements, % of sealed maps (Before -> After): seed 200 add-on: sapling 46 -> 81, plant 44 -> 71, wood 26 -> 49, drink 11 -> 35,
table 4 -> 18, cow 0 -> 6, zombie 0 -> 4, wood sword 0 -> 3. Seed 201 and the whole-model run: sapling 100, plant 98-99, wood 19-20,
table 1-2, cow 7-10, zombie 7-8.

What we found afterwards:
1. On 154 practice views, the trained model wrote a non-move answer 64 times (42%): blends like `spoup`, `dp`, `cp`, `slock`. Its
   valid answers were only `do` (61) and `up` (29). In the last night, 52-70% of moves were still random because the answer was invalid.
2. Crafter ignores moves while the player sleeps, yet the 8 moves before each wake-up are kept: about a third of kept rows a night.
3. In all practice of all three runs, a wood pickaxe happened 3 times (it needs 2 wood for a table, then 1 more wood next to it).
4. The 32-map quiz is noisy: in seed 200 it fell 1.9 points on the last night while the sealed score still rose 0.8.

## What we tried next (one change at a time; marks fixed before each run; 2 seeds each; sealed maps, achievements a game)
| version | change | seed 200 | seed 201 | verdict on our marks |
|---|---|---|---|---|
| GW-S | as above | 3.50 | 3.32 | learns, misses +1.5 |
| GW-S2 | choose among the 17 words by the model's own odds (sample in practice and test) | 2.45 | 2.39 | proved wrong: learned nothing (+0.01, -0.08) |
| GW-S3 | GW-S but drop kept moves made while asleep (half the rows) | 3.29 | 3.43 | no change |
| GW-D | GW-S3 but a learned guesser picks which moves to copy: a value MLP on the view plus RND curiosity, keep the N moves with the highest GAE advantage (N = what the old rule kept) | 1.81 | 3.15 | proved wrong vs GW-S3 |
A correction: our first PPO numbers played PPO's top move. PPO sampling from its own odds gets 3.96 (40,960 moves), 4.15 (57,344),
3.80 (73,728), 3.72 (90,112), 4.40 (230,400), so PPO beats every version above at equal moves.
Details: under GW-S2 the untrained model's own odds already favour one habit (sapling 100% of maps, wood 12% vs 22-26% for random),
so it explored less than random play; 88% of kept moves were its own and copying them changed nothing. GW-D seed 200 shifted toward
crafting (wood 39%, table 10%, wood pickaxe 3%, our best) but lost easy goals (sapling 46 -> 23%, wake-up 90 -> 62%). The guesser's
value ranked the next day's returns with Spearman 0.29-0.56; curiosity was ~68% of credit on day 1, then 3-8%.
Our current reading (suggested): the copy loop only learns from the lucky moments of random play, and the stall comes from that.
Running now (GW-P): a PPO-style night on the model's add-on, with every awake move weighted by its GAE advantage from the same guesser,
clipped ratio against the act rule's odds, entropy 0.01, 4 passes, lr 2.5e-4, sampling from its own odds in practice and test.
Marks: +1.5 over Before, +0.5 over GW-S3, wood pickaxe on 10% of maps, and not behind sampled PPO at equal moves.

## Questions
1. Which explanation of the stall do all these numbers support best: (a) exploration (the loop only copies luck), (b) credit
   (copying rather than weighting by advantage), (c) no memory (one view at a time), (d) a 3M pretrained text model with a small
   adapter is a poor policy learner compared with a fresh 2x256 MLP, or something else? Label each shown / suggested / untested.
2. Is the PPO-style night the right next test? What would make it fail for reasons other than the idea (adapter rank 8, learning
   rate, nightly batches of ~11k moves, the stop rule that ends a run when a 32-map quiz rises less than 1 point over 2 nights)?
3. Propose up to three next changes in order, **one at a time**, each with a pass mark fixed in advance and the result that would
   prove it wrong. Keep compute small (a CPU, a few hours per run).
4. Is our comparison to PPO fair now? What would make it fairer at the same number of moves?
5. End with a short plain-language summary for Ben, a high-school senior: what is going wrong and what to try next, in a few sentences.
