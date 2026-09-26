# dl-5 pass marks: grid nights from go-back search hits (Fix sleep with the thought-memory thread, 2026-09-26)

Registered BEFORE any registered run. Code: scripts/claude_dl5_gridnights.py (runner, marks in score()) and
scripts/claude_gridday.py (the day: rv-385's revert_ban search, pairs, fixed-state scorer; thought-memory thread).
Dev numbers that set the bar (plain 1B, dev seed 38980, 20 grids, 252 states; thought-memory thread): 112 right (44%),
forced states 98/197 (50%), open states 14/55 (25%). Dev day (seed 38970, 150 grids, 60 choices): 79 solved.

## Question
Can copy-practice nights teach the 1B puzzles too deep for guessing, when the day's hits come from go-back search?

## One change from dl-2's S arm
The day is rv-385's revert_ban search on 150 fresh 5x5 Latin grids, 60 choices each, with the arm's own current model;
practice pairs are (state on a solved grid's path, correct next number) in rv-385's prompt and reply prefix. The night
is dl-2's night unchanged (train_copy: 3 epochs, lr 2e-4, batch 8, one growing LoRA r16 on q,k,v,o). No KL anchor.

## Run
MiniCPM5-1B (rev 87179e5c, thinking off). Seeds 8 and 9, 5 nights each. Day d of seed s: grids seed 39100 + 100 s + d.
Arms: S (right numbers), P (placebo: states along the true solution of every grid of that night's day, a wrong number,
legal-looking when one exists, sampled down to S's row count for the same seed and night; P runs no search),
K (report only, seed 8 only: the key's pairs for every grid of the day).
TEST: 60 fresh grids, seed 38990, every state along the true solution; the model's top-scoring number vs the key.
Night 0 = the plain 1B, measured in the same run. Forced = one number fits the visible row and column; open = two or more.
HARM: claude_dl1_nights.harm_panel (300 items); lost = right at base and wrong now.

## Marks (all on the final night; score() computes them)
- G1 slept model better: S >= night 0 + 15 points on each seed.
- G2 right answers caused it: S >= P + 10 points on each seed.
- G2b right answers beat legal-looking wrong ones: on OPEN states, S >= P + 10 points on each seed (there P practises a
  wrong number that fits the visible row and column, so this separates learning from hits from learning the rule).
- G3 no harm: S lost <= 20 on each seed.
- PASS = G1, G2, G2b, G3. Otherwise FAIL.
- INCONCLUSIVE if either S seed trains on fewer than 100 rows on night 1 (the day found too few hits to test the idea).
- PROVED WRONG if, on open states, S <= P on both seeds (right answers teach nothing beyond format and the row rule).

## Report only (no marks)
K per night (ceiling); forced vs open for every arm and night; grids solved and choices used per day; P legal-looking vs
any-wrong counts per night; lost/gained per night; test grids also found in a day (expected 0); the rv-386 first-choice
gate on the final S adapters and on adapter02c (thought-memory thread, from the saved S adapters, never pushed).

## Rules
Additive only. A FAIL stays a FAIL. Blind recount of dl5_results.json against these marks before any report. Adapters
are saved but never pushed. Seeds and test seed above are fixed; nothing is tuned on TEST.
