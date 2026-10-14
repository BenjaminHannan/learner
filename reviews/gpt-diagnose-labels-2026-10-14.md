# Outside-opinion prompt: how can the game model get good practice labels without a hand-written teacher? (written 8:45 AM ET 10-14)

Stand-alone: paste everything below the line into GPT (web), or give it to Astra with the repo (Astra: read game/A22-GWL-MARKS.md, game/A23-GWL-RESULT.md,
game/oracle.py, game/probe.py, game/pg.py, game/mode.py; no edits, no training, no tests, no GPU). It is only about the 3M game-world test (Crafter as text);
it is not about the card experiments or the village model, so do not mix them in.

---

I run a small research project. A 3-million-parameter language model plays Crafter (a flat, top-down Minecraft) as text. Each step it reads a 9x7 letter
map (trees `T`, water `~`, grass `.`, stone `o`, cows `C`, zombies `Z`, the player drawn as `^ v < >` for the way it faces) plus health, food, drink,
energy and what it carries, and it answers with one of 17 move words (`left right up down do sleep table wpick ...`). A word's score is the sum of
its letter log-probs plus an end mark, and the 17 scores are turned into odds with a softmax. Only a small low-rank add-on (rank 8, 135,488 numbers)
trains; the base model is frozen. Score = mean number of distinct achievements ("unlocks") a game on 100 held-out maps. Random play: 2.31.

## What we know (shown = measured in our runs; two seeds, 200 and 201, unless noted)
1. Shown: every way we tried to learn from the game's own reward plateaued near 4 unlocks a game. Copying the 8 moves before each unlock (4 variants): 3.3 to 3.5.
   A learned value guesser picking moves to copy: 1.8 and 3.2. A PPO-clipped night on the add-on (8 nights, about 87,000 moves, learned temperature): 4.15 and 4.19.
   A fixed habit that ignores the map but plays the same move odds as the best of those runs: 3.96 and 3.87, so about half of the +0.4 over the untrained model
   is a move habit. A standard small PPO network given the same number of moves: 3.7 to 4.4 (noisy).
2. Shown (new, "GW-L"): we asked whether the model can read the map at all. A hand-written labeller (a pure function of the view: it finds the nearest tree, water or cow
   by breadth-first search over the walkable cells, steps toward it, uses `do` when facing it, crafts a table and wood tools when it has the wood, plants a sapling,
   walks on, and so on) gives the "right" move for any view. We recorded views from games where each step is the labeller's move half the time and a random move
   the other half, and trained the add-on by cross entropy on the labelled word (fixed constants, 10 epochs, no tuning). The labeller itself, played with our usual 10% random moves, scores
   8.23 unlocks a game on the 100 held-out maps.
   Held-out accuracy is on views where the right move depends on the map (always saying `do` scores 27.2% there); sealed play samples from the model's own odds:
   | labelled views | seed | held-out accuracy | sealed unlocks a game (95% interval vs the PPO-clipped run) |
   |---|---|---|---|
   | 16,000 | 200 | 41.9% | 4.88 (+0.73, 0.28 to 1.17) |
   | 16,000 | 201 | 45.4% | 4.62 (+0.43, 0.04 to 0.82) |
   | 64,000 | 200 | 62.4% | 6.50 (+2.35, 1.87 to 2.79) |
   Training accuracy was still rising at the last epoch in every run, so these are floors. With 64,000 labels the model makes a wood pickaxe on 83% of maps and stone on 40%
   (the PPO-clipped runs: 2 to 3% and 0%). Seed 201 at 64,000 and the 1,000 and 4,000 label runs are still running.
3. So (shown) capacity is not the wall: the 3M model with this add-on and this scorer can learn a map-to-move rule when it is told the answer. What we have not shown is that the model
   can get such labels itself. The labeller is a hand-written teacher; our rule is that everything the finished model does is learned, hand-written code may live only inside an outside tool
   the model chooses to call (like a calculator), and nothing a researcher knows about the game may be needed at run time.
4. Constraints: free CPU only (4 cores; the model plays about 60 moves a second, a training update on 256 views takes about 10 seconds), runs of up to about 10 hours, no GPU, no new
   teacher model. The game can be treated as an outside tool the model calls. Whether the game's world can be copied and stepped forward for look-ahead is untested (it is a Python object with
   random generators; we have not tried).

## What I want from you
1. Label every claim "shown" (follows from the numbers above), "suggested" (plausible, untested) or "untested".
2. The gap is: reward-only learning gives about 4 unlocks, a perfect teacher gives 6.5 at 64,000 labels and 8.2 for the teacher itself. Which cheap, deployable label source (no hand-written game knowledge)
   would most likely close part of that gap? Candidates we see (add others, but then pick one): (A) hindsight labels from the model's own unlocks with a longer or smarter window than "the 8 moves before an unlock";
   (B) search with the game as a tool (copy the world, look ahead, label the first move of the best path found, distil into the add-on, repeat: expert iteration); (C) a learned value or inverse-dynamics
   model used to relabel the model's own recorded moves; (D) something else.
3. Give ONE change to try next, not a list. Fix the pass marks in advance (a number on the 100 sealed maps and a paired-seed rule: >= 6 paired seeds to confirm, two seeds are only a screen),
   say what the baseline is, and state the result that would prove the change wrong.
4. Tell me what you would NOT trust about the numbers above (for example 100-map noise, two seeds, that half of the labelled views come from the labeller's own play, that training had not converged).
5. End with a plain-language summary for a high-school senior: what happened, what you think is going on, what to try.
