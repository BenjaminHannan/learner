# brd-12 plan (draft, not registered): can the lucky-hits loop climb from easy games to harder ones?

Creative thread, written 2026-09-27 05:33 UTC by `date -u`, while brd-11 waits for BensPC. A plan, not a
registration. Nothing here is sealed until its DEV numbers are committed and the Thread manager has seen the marks.

## Why
brd-5..9 and brd-11 all use number puzzles, and both number worlds are now used up. Ben's goal is skill that
carries to new places (15:41) and a model that gets better overnight. A world where the plain 1B gets NO lucky hits
is the real test of that: brd-11's DEV found 0 of 20 on level-1 text games (Sleep research's key and recipe games,
plans 4-6 steps) but 11 of 16 on one-step level-0 key games. So the loop has something to start from only on the
easy level, and the question is whether nights of practice can climb to the level it could not touch.

## Brain first
- Curriculum: animals learn a long chain by first learning its last link (shaping / backward chaining).
- Hindsight: hippocampal replay replays the paths an animal actually walked, not only the rewarded ones; the
  replayed path teaches "how to get to where I ended up". The machine-learning version is hindsight experience
  replay (HER): a failed attempt's legal moves become a correct example for the room they actually reached.
- Guess (labelled): HER is what turns the zero-luck level into something the loop can learn from, because every
  legal walk is a hit for SOME goal, checked by the game's own simulator.

## One change
- Arm A (today's recipe on games): practise level-0 and level-1 key games each night; keep greedy-if-right else the
  first checked hit of 30 samples; nightly LoRA from base on everything kept, 3 nights (brd-9's recipe).
- Arm H: the same, plus HER: for a level-1 game with no hit, each distinct room reached by a sample's legal moves
  becomes an extra example (same maze, goal rewritten to that room, target = the sample's own moves up to that room,
  checked by claude_textgames.check). Cap per game, and matched example counts, to be set from DEV.
- Mark (asked goals only, never relabelled goals): level-1 key games from fresh test seeds, cov@30. Draft PASS:
  H3 − A3 ≥ a fixed bar in every seed with the 95% interval above 0, plus the no-harm part used in brd-11.
- Targets are the model's own checked moves only; the fixed game text is the world's (code-made), loss-masked.

## Before sealing
1. DEV (running): scripts/claude_brd12_dev.py, 10 level-1 key games, 30 samples: how many samples have a legal
   move and how many distinct relabelled goals they give. If HER gives almost nothing, H has nothing to add.
2. Recipes at level 0 (timed out on CPU): measure on BensPC or skip recipes.
3. Seeds: my range 900000-999999; DEV 900000-900999 (already used for DEV), test from 901000.

## Draft marks (added 2026-09-27 05:49 UTC, after the DEV in artifacts/claude-brd12-20260927/DEV-NOTE.md)
DEV result: level 1 gives 0 asked-goal hits in 600 samples but 16 relabelled goals in 20 games at T 1.5.
- Nights: 3, brd-9's recipe (fresh LoRA from base on everything kept, 3 epochs, r16, lr 2e-4, batch 8, LoRA seeds
  0/1/2; the model that slept practises the next night). Each night: 200 fresh level-0 and 200 fresh level-1 key games
  (seeds 902000+), the same games in both arms. Temperature by brd-9's DEV rule (1.0 vs 1.5).
- Arm H: hits on asked goals, plus for each level-1 game with no hit, up to 2 relabelled examples (distinct rooms;
  target = the sample's own moves up to that room, checked by claude_textgames.check).
- Arm A (control, equal examples without repeats): hits on asked goals, plus hits from EXTRA fresh level-0 games
  (practised the same way) until A has as many examples as H that night. Repeats are not used (they collapsed coverage
  in brd-5). So H vs A = "relabelled level-1 walks" vs "more real level-0 hits", at the same example count.
- Test: 240 fresh level-1 key games (seeds 901000-901239), ASKED goals only, 30 samples each; base, night 1, night 3.
- PASS: H3 ≥ A3 + 12 in every seed (seed k vs k), the 95% interval (bootstrap over games) for H3 − A3 above 0, AND
  H3 loses ≤ 20 of Fix sleep's 300 harm items in every seed (a consistency check, as in brd-11).
- "H cannot reach the bar": upper bound of H3 − A3 below 5 points. "H adds nothing": upper bound ≤ 0. Else NOT SHOWN.
- CLIMB line (reported): A3 and H3 vs base on level 1 (base expected near 0).
- Inconclusive: fewer than 100 relabelled examples on night 1.
- Prediction: base 0-3 of 240; A3 5-20; H3 10-35; PASS about 30%.
- Code: not written yet (needs a game-prompt wrapper for claude_blurt2.train_lora). BensPC, $0, after brd-11.
