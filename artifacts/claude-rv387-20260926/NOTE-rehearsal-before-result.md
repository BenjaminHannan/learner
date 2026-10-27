# rv-387: rehearsal finding written BEFORE any 358i result (2026-09-26 15:05 UTC, by date -u)

Additive note; PASSMARKS.md and the sealed code are unchanged. rv-387's rental section launched with 358i at 14:02 UTC.

Rehearsal (unregistered, CPU): a small loop net trained with Sleep research's 358i trial code
(artifacts/claude-rsn358i-20260926/trial/attn_trial.py, loop d256x2, 3,000 steps on 4x4/5x5 legend grids), then
rv-387's three arms at 48 rounds on 60 fresh grids per size (seeds 77100/77101, not the sealed test grids):
- 6x6: KEEP 53, GUESS 53, BACK 53 of 60. 7x7: KEEP 28, GUESS 30, BACK 30 of 60.
- BACK went back 0 times in both sizes: it was identical to GUESS.
Why (same net, 47 guesses on unsolved 7x7 grids, 8 rounds after each guess): the stop head q ROSE after the guess
for right guesses (mean 0.04 -> 0.11) and for wrong guesses (0.09 -> 0.20); it fell after 1 of 32 right and 0 of 15
wrong guesses. Writing any symbol onto the page makes the net more confident, so "q fell below the snapshot's q"
almost never fires.

Added prediction (before the result): P387.4 BACK goes back rarely or never on the 358i nets, so BACK is close to GUESS
and the PASS mark (BACK >= GUESS + 10) is unlikely. The tiny net is weaker than 358i's, so this is suggested, not shown.

Fallback, if rv-387 shows BACK ~ GUESS: a trigger that does not depend on q. Going back on a time slice: after a guess,
the loop gets W rounds; if the checker has not accepted the grid, restore the snapshot and try the next candidate
(the checker is already allowed in every arm). To be tested on practice grids first, then registered as its own
number; it also becomes rv-390's BACK arm.
