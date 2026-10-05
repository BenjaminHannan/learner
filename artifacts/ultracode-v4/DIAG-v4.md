# Ultracode v4 diagnostics: where exactly is the learning blocker?

Written 2026-10-05 01:45 UTC (9:45 PM ET Oct 4), before any of these ran. Fast lane, exploratory. Same rows as the fit screens: worst-8 families, the 2,000 fixed rows of seed 1, trainfit = their first 320, held-out = the 320 in_dist rows of those families. Code: `scripts/cap256_launch/uc_diag_v4.py`; box: `scripts/cap256_launch/ultracode_box.sh` (one Vast RTX 5090, queue in `queue/`).

## Questions and marks (fixed now)

1. **bare (can the frozen 1.2B do these at all?)** Chat template + "only the final answer"; chat template + worked steps then "Answer:"; the raw copy-path format with no prefix.
   - "LM can do them with worked steps" if chat_steps >= 70% on trainfit. "LM can't, even with steps" if < 40%.
   - chat_direct is the no-steps ceiling of the LM alone; compare it with main2 (trainfit 121/320 = 38% at update 0).
2. **chan (can 8 vectors steer the frozen LM to the right answer?)** On up to 64 trainfit rows main2 gets wrong (8 per family), optimise 8 free vectors from main2's own prefix, max 150 Adam steps, placed in front of the question (today's layout), after it, or alone (no question).
   - "front channel is enough" if front solves >= 90% of rows. "front placement is a bottleneck" if front solves < 60% and after-question solves 30+ points more.
   - "alone" says whether 8 vectors can carry the whole answer with no question to read.
3. **direct (can reader+core learn these rows when the signal is clean?)** main2's reader+core plus a new answer-class head on the core state (8 pooled slots x 256), no LM in the loss; 6,000 updates at batch 1 in the fit screen's order (seed 1). MLP head, linear head, and MLP head with a re-initialised core.
   - "core can fit with a clean signal" if MLP-head fit >= 85% at 6,000. "core can't fit even with a clean signal" if < 60%.
   - Held-out is reported (answers never seen among the 2,000 rows count as wrong, and their number is reported).

## How the readings combine
- direct fits and chan front solves: the core can hold the answers and the channel can deliver them, so the fault is the learning signal through the frozen LM. Next: losses or layouts that give the core a stronger signal (two-path loss, after-question vectors).
- direct can't fit: the core itself is the limit for these rows at this budget, so no exit or LM change alone will reach the mark; the fix must add capacity or a different computation route.
- chan front fails where after-question works: placement is a real bottleneck; test after-question vectors on the fit screen.

## Limits
One seed, one box, exploratory. Exact-match scoring. Nothing here touches GOLD-PRIVATE, reserved or blind panels.
