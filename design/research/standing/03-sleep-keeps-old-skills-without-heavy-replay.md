# Standing research 03: sleep that keeps old skills without heavy replay

Written 2026-09-28 (standing research helper, Sonnet). Nothing here was run. Link tags: **A** = abstract page fetched and read on 09-28; **T** = title page only; **M** = from memory, not opened. Labels: shown / suggested / untested.

## What is known in the repo (shown; from the roadmap row 5 and `artifacts/claude-distill-20260928/RESULTS.md`, not recounted by me)
- After adapting to mazes the old kinds drop to 0 of 200 (roadmap row 5). Sleep with a store of 128 true old examples per kind (R128) recovers sums about 150 and grids about 90 of 200.
- A store 8x smaller (16 per kind) collapses old-kind scores to 3 to 26 of 200 for every arm tried (distill RESULTS.md, "Smaller store").
- Matching the loop's own earlier answers (distillation, D128) added only +4.5 of 200 (sums) and +9.75 (grids) over R128, below the 20 bar, and cost 10 to 18 of 300 maze skill at k = 16,384. Doubling the true-answer loss (W128) did as well.
- H6 (sleep length, lr-matched long night) and the vast kit are already queued for the "how long" question. I do not cover it.
So the open question is not "more loss on the same store". It is: how to keep old kinds when the store is small, or when the update was never allowed to wander far.

## Sources
| source | what it says | tag |
|---|---|---|
| Robust fine-tuning of zero-shot models (WiSE-FT), https://arxiv.org/abs/2109.01903 | Averaging the weights of the original and the fine-tuned model keeps most of the original's robustness while keeping most of the new gain. One knob, no extra training. | A |
| Model soups, https://arxiv.org/abs/2203.05482 | Averaging weights of fine-tuned models often helps, because they sit in one low-error basin. | A |
| Editing models with task arithmetic, https://arxiv.org/abs/2212.04089 | Differences of weights can be scaled and added. | T |
| LoRA Learns Less and Forgets Less, https://arxiv.org/abs/2405.09673 | Low-rank updates learn less than full fine-tuning but keep the base model's outside-domain skill better, more than some standard regularisers. | A |
| RL's Razor, https://arxiv.org/abs/2509.04259 | How much is forgotten tracks how far the new model's outputs move from the old one's on the new task; methods biased toward small moves forget less. | A |
| Dark Experience Replay, https://arxiv.org/abs/2004.07211 | Replay plus matching the net's earlier outputs. Same family as the distill test. | A |
| Orthogonal Gradient Descent, https://arxiv.org/abs/1910.07104 | Project new-task gradients away from directions that matter for old data. | A |
| EWC, https://arxiv.org/abs/1612.00796 | Penalise moving weights that mattered for old tasks; importance from a small sample. | T |
| Learning without Forgetting, https://arxiv.org/abs/1606.09282 | Keep old outputs on new inputs, needs no old data. | T |
| Deep Generative Replay, https://arxiv.org/abs/1705.08690 | Replace stored examples with generated ones. | T |
| Biologically inspired sleep algorithm, https://arxiv.org/abs/1908.02240 | Sleep-like offline phase with spike-timing rules cut forgetting in incremental learning on MNIST and CUB200. Abstract read; not a match for our setting. | A |
| van de Ven et al. 2020 "Brain-inspired replay", Nature Communications (page redirected, not opened) | Replay of hidden representations instead of raw inputs. | M |
| Diekelmann and Born 2010, "The memory function of sleep"; Ji and Wilson 2007 (hippocampus-cortex replay) | Sleep replays memories; weakly-encoded ones benefit most (Denis et al. 2020, from memory). | M |
| Tononi and Cirelli 2014, synaptic homeostasis | Sleep scales synapses down globally so learning can continue. | M |
| McClelland et al. 1995, complementary learning systems | Fast hippocampus stores raw episodes; slow cortex learns them interleaved. | M |

## Brain angle (suggested, simplified, not checked here)
- Interleaving keeps the cortex from overwriting: old and new are replayed together, slowly.
- Replay is not uniform. Weakly stored memories are favoured (from memory, tag M). That is a use of a small replay budget the loss does not currently make.
- Global downscaling in sleep: shrinking all weights a little toward a set point is part of sleep, not a bug.
- Where silicon does better: we can keep the raw episodes in full (goals page), keep a copy of yesterday's weights and interpolate to it exactly, and check an overnight change and undo it.

## Leads, ranked (guesses mine, not measured). Pass-bar language below reuses the distill test's bar of 20 of 200 old-kind gain, not a new bar.
**Lead 0 (diagnostic, cheap): where did the forgetting go?** Per parameter group (embedding, shared block, each read head), revert only that group to its pre-maze weights and score old kinds and mazes on the dev panel. If forgetting and maze skill sit in different groups, the answer is "freeze or protect these"; if they sit in the same groups, the small-update leads will cost maze skill. Wrong if every group's revert drops maze skill and old kinds move together. Untested.

**Lead 1 (guess 35%, top pick, eval-only): weight interpolation with the pre-adaptation net.** After adapting to mazes, set weights to (1 - a) x old + a x adapted, choose a on the 16-per-kind store only, no sleep and no training. Report old-kind and maze scores along a in steps of 0.1, next to R128 sleep and the 16-store sleeps. Wrong if no a keeps old kinds at half their pre-maze level (100 of 200) while keeping at least 90% of the maze gain, on both seeds. Caveat: the interpolation may pass through a bad region (nets with different learning histories are not always one basin; model soups' basin claim is for fine-tunes of one start, which this is). Untested.

**Lead 2 (guess 30%): spend the small store on the forgotten items first.** Change only how sleep samples the 16-per-kind store: draw in proportion to current loss on each item (weakest first), same 512 updates, same store. Compare with the same sleep sampling uniformly (fair comparator, 3 sleep draws each, gate margin max(6, 2 x SE) per H8). Wrong if weakest-first is not above uniform by more than the margin on both kinds in both seeds. Risk: with only 16 items it may over-fit them and not the kind (check on the fresh old-kind panel, not the store). Untested.

**Lead 3 (guess 25%): learn the day into a small low-rank piece, fold it in only at sleep.** Change only adaptation: train a low-rank update on the maze day (rank chosen so about 1% of weights), leave the base frozen, so old kinds are untouched by construction until sleep; at sleep merge and replay a small store. Evidence: LoRA forgets less but learns less (A), so the maze rung scores will fall; the test is whether old-kind retention rises more than maze skill falls. Wrong if F_eq drops more than the noise (about 10) with no old-kind gain over R128 at the same store. Untested.

Not ranked: EWC from a 16-example store (replay-free but known to be weak beyond small tasks; guess 15%, untested), OGD (needs gradient storage), generative or hidden-state replay (our net is a solver and cannot write puzzles; would need a new head).

## Marks reminders (H8 checklist)
Sleep gates: mean of 3 sleep draws, margin max(6, 2 x SE). Comparator is the higher of R128 sleep and the no-sleep interpolation. Include a plain-net row.

## Not checked / risks
- Abstracts only. None of these papers used tiny recurrent solvers; WiSE-FT and LoRA results are from large pretrained models.
- I did not check what the harness sleep does about learning-rate decay, or whether H6's arm B already touches weakest-first sampling; a quick read of `Learner.sleep` before running Lead 2 is advised.
