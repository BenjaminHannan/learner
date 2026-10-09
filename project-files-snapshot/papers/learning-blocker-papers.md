# Papers for the learning blocker (2026-10-04)

Blocker: frozen LFM2.5-1.2B + ~9M looped core + 32-wide, 8-vector exit StatePrefix. Core can't fit 2,000 practised skill rows (48% vs 85% mark), multi-step skills ~15%, and on new kinds the frozen LM answers alone.
Already known, not repeated: 2609.36585, 2610.00673, 2609.33134, and arxiv-bangers-scan.md.
"Read" column: **abstract** = I opened the arXiv abstract page; **snippet** = only the title and a search-result summary; no claim below is checked beyond that. This list only finds papers; it proposes no fixes.

## A. Frozen LM + small trainable module (closest to our setup)

1. **Exploring System 1 and 2 communication for latent reasoning in LLMs** — https://arxiv.org/abs/2510.00494 — **abstract**
   - Frozen base + trained coprocessor swapping latent messages; wider channel and joint finetuning tested; a single-model baseline nearly matches the best two-part design, so the gains look like extra compute.
   - Bears on: "narrow exit" suspect (they vary channel capacity) and whether the frozen LM is the ceiling (their joint finetuning arm).
2. **Latent Recurrent Thoughts: Recurrent Refinement of Proposed Latents for Reasoning with Frozen LLMs** — https://arxiv.org/abs/2609.01117 — **abstract**
   - Small recurrent reasoner refines latent vectors fed as soft tokens to a frozen LLM; beats earlier frozen-decoder latent methods on Countdown, Sudoku and NL reasoning.
   - Bears on: our exact shape (frozen LM, small recurrent core, soft-token exit) and multi-step failure.
3. **Deliberation in Latent Space via Differentiable Cache Augmentation** — https://arxiv.org/abs/2412.17747 — **snippet**
   - Frozen decoder; a coprocessor writes latent embeddings into the KV cache (reaches all layers), trained with the decoder's LM loss.
   - Bears on: exit design. Writing into the cache at every layer instead of a prefix at the input.
4. **Thinking in Latents: Adaptive Anchor Refinement for Implicit Reasoning in LLMs** — https://arxiv.org/pdf/2603.15051 — **snippet**
   - Frozen backbone; trains only learnable anchor embeddings and projection modules.
   - Bears on: exit/projection design with a frozen LM.
5. **Trained Persistent Memory for Frozen Decoder-Only LLMs** — https://arxiv.org/pdf/2603.22329 — **snippet**
   - Compares adapters (parallel cross-attention, KV extension, etc.) on a frozen GPT-2.
   - Bears on: which interface (prefix vs cross-attention vs KV) carries more.
6. **G-MemLLM: Gated Latent Memory Augmentation for Long-Context Reasoning** — https://arxiv.org/html/2602.00015 — **snippet**
   - Frozen LLM + trainable latent memory bank with gating.
   - Bears on: the gate between core and LM (our "core adds nothing on new kinds").
7. **Learning Evidence Highlighting for Frozen LLMs** — https://arxiv.org/pdf/2604.22565 — **title only**
   - Small module steers a frozen LLM's attention to evidence. Bears on: pointer/relevance step.

## B. Soft prompt / prefix capacity

8. **Fundamental Limits of Prompt Tuning Transformers: Universality, Capacity and Efficiency** — https://arxiv.org/abs/2411.16525 — **abstract** (+ snippet claim)
   - Abstract: single-layer prompt tuning is universal in theory. Snippet (not verified): memorizing a dataset needs prompt length that grows exponentially.
   - Bears on: whether 8 vectors can ever hold enough per-question content.
9. **Universality and Limitations of Prompt Tuning** — https://arxiv.org/pdf/2305.18787 — **snippet**
   - Theory of what prompt tuning can and cannot express on a frozen transformer.
   - Bears on: the ceiling of a prefix-only exit.
10. **InfoPrompt: Information-Theoretic Soft Prompt Tuning** — https://arxiv.org/pdf/2306.04933 — **snippet**
    - Treats the soft prompt as an information channel into the frozen model.
    - Bears on: width/information in the exit.
11. **SelfCP: Compressing Over-Limit Prompt via the Frozen LLM Itself** — https://arxiv.org/abs/2405.17052 — **snippet**
    - Compresses long prompts to a few memory tokens using the frozen LLM as the compressor (about 12x).
    - Bears on: how many vectors are needed to carry a question's content.
12. **R-Capsule: Compressing High-Level Plans into Latent Tokens** — https://arxiv.org/abs/2509.22131 — **snippet**
    - Information-bottleneck latent plan tokens. Bears on: a deliberately narrow exit.

## C. Looped / recurrent-depth models on multi-step and state tracking

13. **When Does Recurrence Become an Algorithm? Convergence Selection in Weight-Tied Looped Transformers** — https://arxiv.org/abs/2607.20594 — **abstract**
    - Training sets a "computation frontier" tied to train steps/iterations; architecture decides which algorithm emerges; learning difficulty follows the operators, not complexity class.
    - Bears on: why chain_ops/state_update stall at 4-8 loops.
14. **Thinking Deeper, Not Longer: Depth-Recurrent Transformers for Compositional Generalization** — https://arxiv.org/abs/2603.21676 — **abstract**
    - Shared-weight block iterated for variable depth; extrapolates beyond training depth; snippet adds a learned step embedding per iteration (not verified).
    - Bears on: multi-step skills and loop-count handling.
15. **Loop the Loopies!** — https://arxiv.org/pdf/2607.16051 — **snippet**
    - Looped transformers on in-context learning and multi-step tasks.
16. **LT2: Linear-Time Looped Transformers** — https://arxiv.org/pdf/2605.20670 — **snippet**
    - Synthetic tasks mixing state tracking and retrieval; says state tracking favours recurrent depth.
    - Bears on: state_update.
17. **Looped Transformers with Source-Centered State Evolution** — https://arxiv.org/pdf/2607.27656 — **snippet**
    - Hidden-state dynamics problems at large recurrent depth.
18. **Adaptive Depth in Looped Transformers: Diagnosing Learned Halting Gates and Trajectory Readouts** — https://arxiv.org/abs/2607.20519 — **title + snippet**
    - Looks at the readout from the loop trajectory. Bears on: the exit read.
19. **The Topological Trouble With Transformers** — https://arxiv.org/abs/2604.17121 — **snippet**
    - Argues feed-forward transformers limit dynamic state tracking.

## D. Prefix vs weight-change expressivity

20. **Prompt tuning vs LoRA expressivity** (search summary, see 2305.18787 above and LoRA-vs-prompt-tuning memorization comparisons) — **snippet only, source paper not identified.** Claim to check: LoRA memorizes n examples with O(n) parameters while prompt tuning may need more, and prefixes cannot change the LM's attention maps.
    - Bears on: frozen-LM-as-ceiling. Pairs with the already-known 2609.36585.

## Top 5 for the blocker
1. 2510.00494 (channel capacity + joint finetuning, tested head-on)
2. 2609.01117 (same shape as ours: frozen LM, small recurrent reasoner, latent exit)
3. 2412.17747 (cache-level exit instead of a prefix)
4. 2607.20594 (why weight-tied loops stall on multi-step)
5. 2411.16525 / 2305.18787 (prefix capacity theory)
