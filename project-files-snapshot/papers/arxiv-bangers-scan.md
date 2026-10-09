# arXiv Bangers scan (2026-10-04)

Source: https://arxivb.org/ (arXivbangers, 29 listed papers). Only the first four entries below had their abstracts opened; the rest are judged from the site's one-line blurbs and are marked (blurb only).

## Ranked

1. **Transformers Stop Thinking Too Early, and a Tiny LoRA Fixes It** https://arxiv.org/abs/2609.36585
   - A rank-8 LoRA at an early layer, with all weights frozen, lets models follow far longer reference chains (Qwen3-8B 15.5% -> 99% on 24-line chains).
   - Problems 1, 3 and 2: a tiny add-on to a frozen LM that fixes multi-step following. Most directly comparable to our frozen-1.2B setup.
2. **Closing the Loop: Practical Training Recipes for Looped Language Models** https://arxiv.org/abs/2610.00673
   - From-scratch looped LM on 310B tokens instead of 7.7T; adapts a dense model to loops with one input-mixing scalar plus a smoothed exit loss; 1.4B looped beats parameter-matched dense on 12/12 benchmarks (GSM8K +14).
   - Problems 2 and 3: our core is a looped latent; their exit-gate regularization and input mixing are candidates for the exit-pipe suspect.
3. **Ceiling of a Task: When Can a Transformer Succeed Without Its Chain of Thought?** https://arxiv.org/abs/2609.33134
   - Proves serial tasks (chains of steps) cannot be answered by one shallow pass; replacing the chain with filler drops accuracy to a fixed ceiling.
   - Problems 2 and 3: may explain why multi-step rows (chain_ops, state_update) cap at ~15%: if the exit is one shallow pass, the loop must carry the steps.
4. **SkillGym: Internalizing Human Skills into LLMs** https://arxiv.org/abs/2609.27717
   - Turns written skills into verified training environments (2,756 environments, 8,364 successful trajectories) and fine-tunes so skills work without being in the prompt.
   - Problem 3 and the skills curriculum: a recipe for generating verifiable skill tasks.
5. **Looped Diffusion Transformer** https://arxiv.org/abs/2609.40305 (blurb only)
   - A 260M model with repeated blocks beats models 6.5x larger.
   - Problem 4: evidence that looping can replace size.
6. **Self-Play Pretraining with Zero Data** https://arxiv.org/abs/2609.30063 (blurb only)
   - Zero-shot scaling from self-play on synthetic sequences, no human data.
   - Problem 1: possible route to generalizing across question kinds.
7. **Fine Until Fine-Tuned: Repeated Solutions Make Reasoning Fragile** https://arxiv.org/abs/2609.33559 (blurb only)
   - Training on repeated solutions makes reasoning brittle under tuning.
   - Problems 1 and 2: relevant to our 97% practised vs poor new-kinds gap.
8. **Context Language Models** https://arxiv.org/abs/2609.37725 (blurb only)
   - Treats context as an editable file the model manages natively.
   - Roadmap: notebook memory.
9. **Match the Distribution, Not the Compute: Post-Training Multi-Token Prediction Heads** https://arxiv.org/abs/2610.00888 (blurb only)
   - Cheap speculative-decoding heads added after training.
   - Problem 4: cheaper/faster talker.
10. **Why Adaptive Optimizers Underestimate Rare Tokens** https://arxiv.org/abs/2609.37535 (blurb only)
    - Adam-style optimizers under-learn long-tail items.
    - Problem 2: a possible reason rare question kinds do not fit.
11. **Training Object Permanence in World Models** https://arxiv.org/abs/2609.28654 (blurb only) - roadmap: vision/Minecraft.
12. **Recursive Self-Improvement via On-Policy Distillation for Reasoning** https://arxiv.org/abs/2609.30652 (blurb only) - Problem 4: distilling into something smaller.

Skipped as not relevant: safety/supply-chain eval, music generation, robotics data, BF16 attention gradients, sparse/linear attention, agent-harness and context-compaction papers.
