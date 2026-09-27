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
