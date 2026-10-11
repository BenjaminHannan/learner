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

## What we plan next (one change at a time)
GW-S2: the model chooses among the 17 legal words by its own odds (the probability of writing each whole word). Practice games sample
a move from those odds; quiz and sealed scoring play the top-rated move. Everything else is unchanged. Marks, fixed before training,
per seed (2 seeds): After - Before >= +1.5 (proved wrong < +0.5); After minus the old loop's After >= +0.5 with the interval above 0
(proved wrong if <= 0 on both seeds); wood pickaxe on >= 10% of sealed maps (proved wrong <= 2%).

## Questions
1. Which explanation of the stall do these numbers support best: (a) how a move is picked (letter blends, argmax of near-flat targets),
   (b) credit (copying 8 mostly random moves before an unlock, including moves the game ignored), (c) no memory (one view at a time),
   (d) too small a model, or something else? Label each shown / suggested / untested.
2. Is sampling from the model's own odds during practice (and top move at test) the right first change, or is there a cheaper or more
   telling one? Will it collapse back to one habit (seed 201 already went to "sapling and plant every game")?
3. Propose up to three next changes in order, **one at a time**, each with a pass mark fixed in advance and the result that would
   prove it wrong. Keep compute small (a CPU, a few hours per run).
4. Is our comparison to PPO fair as described? What would make it fairer at the same number of moves?
5. End with a short plain-language summary for Ben, a high-school senior: what is going wrong and what to try next, in a few sentences.
