# Outside-opinion prompt: why did learning at temperature 1 not help the game-world model? (written 8:50 PM ET 10-12)

Stand-alone: paste everything below the line into GPT (web) or send it to the API judges. It cannot see our repo. This is only the
3M game-world test (Crafter as text); it is not about the card experiments or the village model, so do not mix them in.

---

I run a small research project. A 3-million-parameter language model plays Crafter (a flat, top-down Minecraft) as text. Each step it
sees a 9x7 letter map plus health, food, drink, energy and inventory, and answers with one of 17 move words. It teaches itself in
"nights": it plays 64 games, then updates a small low-rank add-on (rank 8, 135k parameters, the model's own weights frozen) with a
PPO-clipped policy-gradient step on its own tries. Reward = a game unlock (collect wood, place table, eat cow, ...). Scoring is the
mean number of distinct unlocks per game on 100 held-out maps (the "sealed" maps).

## What we know (shown = measured in our runs)
1. Shown: the untrained model, sampling its own move odds divided by a temperature T0 ~ 20 (fitted so entropy = ln17/2), scores 3.75 / 3.61
   unlocks a game on the sealed maps (seeds 200 / 201). Random play scores 2.31. A fixed habit that ignores the map (say "do" 55%, "up"
   25%, same odds) scores 3.78 / 3.67, so the untrained model is not reading the map. A move word's score is the SUM of its letter
   log-probs plus an end mark, not length-normalised, which favours two-letter words ("do", "up"); we suspect this but have not tested it.
2. Shown (GW-P8): 8 nights of PPO-clipped learning at T ~ 20 (T learned, stayed ~20) gave 4.15 / 4.19 (+0.40 / +0.58 over the untrained
   model). Per-night policy change (approx KL) was only 0.004-0.011, with 3-11% of ratios clipped.
3. Idea we tested (GW-PC): dividing log-probs by T ~ 20 makes every policy step about 20x smaller, so first copy the T0 policy into the
   add-on (distillation, held-out KL 0.04-0.05 nats, T = 1 afterwards), then learn at T = 1. Everything else identical.
4. Shown (GW-PC, 6 of 8 nights; the Mac died in night 7): the distilled policy is a fair copy (night 0: 3.79 / 3.69 vs 3.75 / 3.61).
   Per-night approx KL was 2.2x / 2.5x GW-P8's (we wanted 3x), the PPO clip fired on 17-26% of ratios (GW-P8: 3-11%), the learned T
   crept from 1.00 to 1.048, and the practice quiz (32 worlds) did not rise (17.0 -> 16.1; 17.5 -> 16.1). On 50 sealed maps at night 6
   GW-PC scored 3.54 / 3.56 against GW-P8's 4.14 / 4.02 at the same night (paired difference -0.60 (-1.0, -0.2) and -0.46 (-0.82, -0.10)).
5. Nights are ~65 minutes each; each night has ~9,000-10,000 new rows from 64 games of ~170 steps.

## Two explanations we cannot separate
A. The limit is the optimiser: the clip and the learning rate cap the step, so a bigger "natural" step just clips more. Fixing the
   clip, the learning rate or the batch would help.
B. The limit is the signal and exploration: rewards are rare, credit runs across ~170 steps, and the T ~ 20 policy's flat odds were a
   free exploration bonus that T = 1 removes. More step size cannot help; better credit or explicit exploration would.

## What I want from you
1. Label every claim "shown" (follows from the numbers above), "suggested" (plausible, untested) or "untested".
2. Say which of A or B (or a third explanation) the numbers favour, and what in the numbers is evidence for it.
3. Give ONE change to try next, not a list. Fix the pass marks in advance (a number and a paired-seed rule: >= 6 seeds to confirm, two
   seeds are only a screen), and state the result that would prove the change wrong.
4. Tell me what you would NOT trust about the numbers above (for example 50-map noise, two seeds).
5. End with a plain-language summary for a high-school senior: what happened, what you think is going on, what to try.
