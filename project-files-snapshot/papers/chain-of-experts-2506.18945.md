# Chain-of-Experts (arXiv 2506.18945) and what it means for us

Read 2026-10-05, 7:40 AM ET, for Ben's link. No training run.

## In plain words

Mixture-of-experts layers normally pick a few small sub-networks ("experts") once per word and run them side by side. This paper runs them one after another inside the layer: pick some experts, apply them, then pick again based on the new result. The one result that matters for us: if you loop like this, **each pass needs its own router**. Reusing one router on every pass was worse than not looping at all.

Our thinker loops 4 rounds and reuses one router on every round, so it is the bad case. The paper's evidence is weak, though, and our blocker is not thinker capacity. Worth one cheap test, not a redesign.

## The paper (Wang, Pan, Yao, Csordas, ... Shiwei Liu; June 2025)

- Setup: 4-layer, 544M-parameter MoE (scaled-down DeepSeek-V2-Lite), 63 routed experts + 1 shared. Baseline picks 8 experts once; CoE picks 4, applies them, picks 4 more (2 iterations, same expert compute). Trained 2,000 steps x 64 x 512 tokens (about 65M tokens) on MetaMathQA and/or SlimPajama, one H100, about an hour per run.
- Shown in the paper: MetaMathQA validation loss 1.20 -> 1.12 at matched expert compute. 2 iterations matched 3x wider expert selection with 17.6-42% less memory.
- Shown in the paper (the ablation that applies to us): sharing one router across iterations "quickly plateaus around 1.5, worse than both standard CoE and the MoE baseline" (Fig. 7). A residual inside each iteration beat an outer-only residual (1.12 vs 1.21).
- Weak spots: downstream accuracy is at chance for every arm (ARC-E 26-28%, HellaSwag 25-27% on 4 choices), so there is no accuracy evidence, only loss. One small scale, 2 iterations only, and some wall-clock overhead versus plain MoE. Authors: "the comparison has not yet shown a significant gap."

## Our thinker, checked in code (branch claude/ultracode-learning-blocker-gh011t)

- Shown: each core block's MLP is an 8-expert, top-2 MoE (`scripts/sol_spatial_attention_core.py:19-43`, `UpcycledMLP`).
- Shown: the loop reuses the same blocks, so the same router, on every round (`sol_spatial_attention_core.py:98-99` calls `step`, which runs `self.blocks` each time, `scripts/claude_fewex_net.py:77-81`). This is the paper's "shared gating" arm.
- Shown: in main2-based cores the router starts at exactly zero (`sol_spatial_attention_core.py:26`) and experts start as equal copies. With zero logits every token goes to experts 0 and 1 at weight 0.5. Those two get identical gradients, so the router gets none and experts 2-7 never train (already recorded in `docs/premonition-status/LIVE.md`). About 1.6M of the core's ~9M parameters are live. For the "whole size" comparison, the honest core size is about 1.6M.
- Shown: the planner runs that use `--fresh-core` (PLS, PLCD) reset every layer (`uc_diag_v4.py:66-70`), so their routers start random and the MoE is alive there. But the balance loss is not in the loss, and one router still serves all 4 rounds.
- Suggested, not shown: in PLS (matched practice) the plan's weak part is the ops (135.0 / 160) more than the pointers (144.5 / 160), and seed 3's op head never learned state_update (9 / 40). Choosing an op per step is the kind of per-round decision a per-round router could help with.
- Untested: whether a per-round router helps a 256-wide, 4-round core at a few thousand updates. The paper only shows a 544M model at 65M tokens.

## One test: per-round routers in the planner (belongs to the ultracode blocker thread)

One change from PLS: each block gets 4 routers, one per round (the experts stay shared). That adds 2 blocks x 4 x (256 x 8 + 8), about 16k parameters (~0.2% of the core). Everything else stays bit-identical to PLS: fresh reader+core, `--op-attend`, `--lr-cosine`, `--screen-rows`, seeds 1-6, the same 160 held-out chain rows. Router init is the same as PLS (random), and the balance loss stays out of the loss.

PLS baseline held plan-exact, seeds 1-6: 140 / 141 / 112 / 131 / 138 / 133, mean 132.5 (82.8%). LM steps on the same seeds: mean 137.3.

Marks, fixed before running:
- **Pass:** 6-seed mean >= 137.3 (level with the LM's steps, +3 points over PLS) AND ahead of PLS on at least 5 of 6 paired seeds.
- **Proves it wrong:** mean gain under 1.6 rows (1 point) OR ahead on 3 or fewer seeds. Then drop per-round routing.
- In between: inconclusive, do not adopt.
- **Void if** the logged per-round expert counts are near-identical across rounds (the change did not take).
- Secondary readout (not a mark): ops vs pointers split, and whether seed 3 learns state_update.

Compute: PLS-sized runs (about 2,700 updates) on Ben's 5070 Ti or M1 Pro, never Vast.

If it passes, the custom reader/talker thread's design B (program + calculator) is the next place to try it, since that is a from-scratch looped planner too.
