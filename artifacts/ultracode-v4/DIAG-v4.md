# Ultracode v4 diagnostics: where exactly is the learning blocker?

Written 2026-10-05 01:32 UTC (9:32 PM ET Oct 4), before any of these ran (commit 0f6e0ce08; jobs started 01:33 UTC). Fast lane, exploratory. Same rows as the fit screens: worst-8 families, the 2,000 fixed rows of seed 1, trainfit = their first 320, held-out = the 320 in_dist rows of those families. Code: `scripts/cap256_launch/uc_diag_v4.py`; box: `scripts/cap256_launch/ultracode_box.sh` (one Vast RTX 5090, queue in `queue/`).

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

## Added 01:35 UTC, before it ran: a generation-layout bug check (job 06)
Reading `skills_pretrain_v1.py` with `--copy-path`: `ad.forward` is patched to `with_prompt(o_fwd(...))`, but `o_fwd` (StatePrefix.forward) calls `self.project_training`, which is the *patched* instance attribute, so generation appends the prompt twice: the LM sees `[pooled][prompt][prompt][BOS]` at generation but `[pooled][prompt][BOS]` in training. The zero-pool lesion then also zeroes the first prompt copy, and the shuffle lesion swaps twice per row (so v3's S scores the current row's own vectors). Every copy-path fit/held-out number so far is a generation score, so all of them were measured on the doubled layout.
- New flag `--gen-fix` makes generation use exactly the training layout; each eval now logs `gen-layout` (LM input length before BOS) so the bug is visible directly (buggy = 8 + 2N, fixed = 8 + N).
- Job 06 scores main2 (no training) on the seed-1 trainfit rows and the 320 worst-8 held-out rows, with and without the fix, then on all 1,360 in_dist rows with the fix, intact / zero-pool / shuffle-pool.
- Marks: "the doubled prompt hurts" if the fix raises trainfit or held-out by 5+ points. Lesions under the fix: "core carries question-specific information" if shuffle drops 20+ points below fixed intact; "core carries little" if within 10 points; zero-pool reported.

## Added 02:10 UTC, before they ran: geometry, lesions under the training layout, exit capacity (jobs 09, 10)
From the critic pass of the understand workflow. All teacher-forced on the training layout `[pooled][prompt][BOS]` (teacher-forced exact = greedy exact when the layouts match), main2, no training. Rows: seed-1 trainfit (320) and worst-8 held-out (320).
- **09 geom.** Fixed point: mean relative change of h per round (rounds 2-8) and |e|/|h|. Mark: "loop is a contraction" if the change at round 4 is below 1e-2. Prefix geometry: mean pairwise cosine of pooled prefixes, spread around the family mean. Lesions: intact vs family-mean prefix vs global-mean prefix vs same-family shuffle vs 8 rounds. Marks: "core is a mode signal (c)" if the family-mean lesion is within 3 points of intact on trainfit; "core carries row content" if it drops 15+ points.
- **10 exitcap.** On up to 64 main2-wrong trainfit rows (8 per family), optimise (i) the core output h (N x 256) through the frozen exit, (ii) the exit's per-token hidden (N x 32) through its last layer and chunk means; max 150 Adam steps. Mark: "the exit is not the limit (b out)" if (i) solves >= 90% of rows; "the exit is a limit (b)" if (i) solves < 50% while free vectors solved 64/64.
