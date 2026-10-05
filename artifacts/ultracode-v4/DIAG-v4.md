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

## Added 02:05 UTC, before they ran: geometry, lesions under the training layout, exit capacity (jobs 09, 10)
From the critic pass of the understand workflow. All teacher-forced on the training layout `[pooled][prompt][BOS]` (teacher-forced exact = greedy exact when the layouts match), main2, no training. Rows: seed-1 trainfit (320) and worst-8 held-out (320).
- **09 geom.** Fixed point: mean relative change of h per round (rounds 2-8) and |e|/|h|. Mark: "loop is a contraction" if the change at round 4 is below 1e-2. Prefix geometry: mean pairwise cosine of pooled prefixes, spread around the family mean. Lesions: intact vs family-mean prefix vs global-mean prefix vs same-family shuffle vs 8 rounds. Marks: "core is a mode signal (c)" if the family-mean lesion is within 3 points of intact on trainfit; "core carries row content" if it drops 15+ points.
- **10 exitcap.** On up to 64 main2-wrong trainfit rows (8 per family), optimise (i) the core output h (N x 256) through the frozen exit, (ii) the exit's per-token hidden (N x 32) through its last layer and chunk means; max 150 Adam steps. Mark: "the exit is not the limit (b out)" if (i) solves >= 90% of rows; "the exit is a limit (b)" if (i) solves < 50% while free vectors solved 64/64.

## Added 04:23 UTC, before they ran: core test battery PR and LD (design panel, `PANEL-v4.md`)
Asked of this round (Ben wants the core, not the LM, to do the reasoning): why can't the core compute? Both are fast, LM-free or eval-only, box B.
- **PR (probe):** `uc_diag_v4.py --mode probe` on main2 and on a random reader+core (`--fresh-core`). Do number identities survive LM features f -> 32-wide reader r32 -> e -> h1 -> h4? Token probe on number tokens (1-NN and ridge, held tokens with seen values), row probe (ridge R2 for x0, step1, answer on the 4 chain families).
  - Marks (fixed now): "reader bottleneck destroys number identity" if f >= 90% and r32 < 50%; "identity reaches the core" if h4 >= 80%; "the loop loses identity" if e >= 80% and h4 < 50%; "final layer lacks identity" if f < 50%. Row probe: "the core makes the first step more visible" if R2(step1|h4) >= R2(step1|f) + 0.10 and >= 0.5; "the core adds nothing" if R2(step1|h4) <= R2(step1|f).
- **LD (learning ladder):** `--mode direct --head vocab --families chain_ops,state_update,chain_story2,var_chain --warmup 200`, 2,000 rows x 3 passes, held-out = their 160 in_dist rows (single-token targets only; drops reported). Learners: main2 core, fresh core, lmread (linear readout of the LM features, no core), tfm (a generic 4-layer d=256 transformer on the LM features). Targets: step1 (first intermediate value) and answer.
  - Marks (fixed now), held-out: step1 "one step is learnable here" if any learner >= 50%; "regime limit" if all four <= 25%; "core-specific defect" if max(lmread, tfm) >= max(core, fresh core) + 15 points; "the core computes one step" if max(core, fresh core) >= 50% and >= lmread + 10. answer: "a generic learner computes the chains" if tfm or lmread >= 40%; "answer-only regime limit" if all three <= 15%.
- The conditional follow-ups (OR, PL, LDD, DS, FZ) and their marks are in `PANEL-v4.md`; each is added here with its own timestamp before it runs.

## PR result (job 26, read 04:27 UTC)
Number-token identity on held tokens (best of 1-NN and ridge; 1,389 tokens, 99% with values seen in training): LM features f **98.5%**; main2's 32-wide reader hidden r32 **17.6%**; e 15.7%; h1 8.6%; h4 **8.9%**. A random (fresh) reader keeps more: r32 29.8%, h4 24.8%. Row probe R2 for step1: f 0.22, r32 0.09, h4 0.085 (main2).
- By the marks: **"reader bottleneck destroys number identity"** (f >= 90% and r32 < 50%). Not "identity reaches the core" (h4 8.9% < 80%). Row probe: **"the core adds nothing"** (R2(step1|h4) <= R2(step1|f)).
- Per the decision tree: OR is skipped (it would fail for an input reason). LD runs as planned (the lmread and tfm learners read the full 2,048-wide f, so they test whether a small learner can learn the step when it does see the numbers).
- LD smokes (60 updates, each learner) ran clean; 23 / 1,977 fixed rows and 1 / 160 held rows are dropped for multi-token step1 targets (all var_chain).
