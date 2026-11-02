# Near-miss (fork) preference pairs for agent DPO

Scope: prior work on step- and turn-level preference pairs for LLM agents, then five recommendations for the fork-pair design. Searches only, no paper full texts were read, so numbers marked "abstract" come from abstract pages and secondary summaries. Verify before citing.

## Papers

| Method (year) | Branch point | Labelling | Pairs | Saturation fix / evidence |
|---|---|---|---|---|
| **Step-DPO** (2024), [arXiv 2406.18629](https://arxiv.org/abs/2406.18629) | Reasoning step in a math solution | Step correctness (not described in abstract) | 10K step pairs (abstract) | Qwen2-72B-Instruct: MATH 70.8, GSM8K 94.0 (abstract; no pre-DPO baseline given). No full-solution DPO comparison in abstract. |
| **IPR** (EMNLP 2024), [arXiv 2406.11176](https://arxiv.org/abs/2406.11176) | Agent step: the agent's new action is compared with the matching expert step | Monte Carlo step rewards; mismatches become contrastive pairs | Not confirmed | Summary reports +4.5% average over SOTA; WebShop case where ETO made a wrong product choice and IPR did not. Whether the loss is DPO is unconfirmed. |
| **ETO** (ACL 2024), [arXiv 2403.02502](https://arxiv.org/abs/2403.02502) | Whole trajectory (failed vs successful) | Environment reward | Not confirmed | DPO on failed/successful pairs, iterated. Llama-2-7B on WebShop, ScienceWorld, ALFWorld. Summaries claim beats RFT/PPO; no table numbers retrieved. |
| **Agent Q** (2024), [arXiv 2408.07199](https://arxiv.org/abs/2408.07199) | MCTS node expansion over web pages | Q-value plus feedback-model score | Not confirmed | Uses DPO on MCTS pairs. A third-party aggregator lists 50.5% on WebArena (GPT-4o); unverified. |
| **MCTS-DPO** (2024), [arXiv 2405.00451](https://arxiv.org/abs/2405.00451) | Reasoning step from MCTS | MCTS value estimates | Not confirmed | Gains on GSM8K, MATH, ARC-C (from search snippet). |
| **Critical tokens / cDPO** (ICML 2025), [arXiv 2411.19943](https://arxiv.org/abs/2411.19943) | Token-level: tokens whose change flips the outcome | Contrast of positive vs negative fine-tuned models' likelihoods | Not confirmed | Token-level DPO weighted by the likelihood gap. Tested on GSM8K and MATH500, not agents. |
| **Forking tokens / 80-20** (NeurIPS 2025), [arXiv 2506.01939](https://arxiv.org/abs/2506.01939) | Top 20% entropy tokens | Not a pair method: policy gradient masked to high-entropy tokens | n/a | Qwen3-32B: +11.04 AIME'25, +7.71 AIME'24. Training only on the lowest-entropy 80% drops performance. This is RL, not DPO. |
| **AgentRM** (2025), [arXiv 2502.18407](https://arxiv.org/abs/2502.18407) | Tree-search step | Process rewards as MC Q-values | Not confirmed | Compares explicit vs implicit reward models and LLM-as-judge. |
| **Agentic-DPO** (2026), [arXiv 2607.10601](https://arxiv.org/abs/2607.10601) | Each expert state: one-step policy sample vs expert action | Expert action is positive; plausible wrong actions are negatives | Not confirmed | No rollouts. tau-bench retail, 9B: SFT 21.7% to 41.4% (abstract). Claims parity with online GRPO on same backbone. |
| **ToolGraph + DPO** (2026), [arXiv 2606.23112](https://arxiv.org/abs/2606.23112) | Divergence point found by state matching and prefix alignment | Filtered by action-correctness annotation | 161 pairs | tau2-bench, 375 tasks: baseline 0.304, ToolGraph+DPO 0.355. DPO gain concentrated in airline and retail. Notes chosen-reward positivity as a useful checkpoint signal. |
| **NAT** (NAACL 2025), [ACL Anthology 2025.naacl-long.378](https://aclanthology.org/2025.naacl-long.378) | Not step-level: uses failed trajectories directly in training | Environment outcome | Not confirmed | Claims to beat SFT, DPO, and PPO in low-resource settings. |
| **AgentRefine** (ICLR 2025), [arXiv 2501.01702](https://arxiv.org/abs/2501.01702) | Erroneous turns | Refinement from environment feedback | n/a | Masks incorrect steps from the loss. Training on erroneous tokens cut SciWorld performance by about 75% in their ablation. |

## Answers to the specific questions

- **Branch-point choice.** Step-DPO and IPR pick steps from the agent's own trajectory or expert trajectory. Agentic-DPO picks every expert state. Forking-token work uses entropy alone. No retrieved paper uses a confident-decision threshold like p1 ≥ 0.9 with a runner-up floor of 0.005. Untested.
- **Labelling.** Agent Q, MCTS-DPO, and AgentRM use MCTS or rollout values. IPR uses MC step rewards. Agentic-DPO uses no rollouts and treats the expert action as the winner. The ToolGraph paper uses action-correctness annotations. Environment-outcome labels from forked branches (your plan) are the closest to ETO and to the ToolGraph filter.
- **Pair counts.** Step-DPO used 10K. The ToolGraph paper used 161 on tau2. Other pair counts were not confirmed.
- **Saturation and fixes.** I found no paper that reports DPO saturating in the way you saw. ToolGraph reports a positivity checkpoint signal, which is a monitor, not a fix. Length-normalised and reference-free variants (SimPO) are reported to help over DPO on AlpacaEval 2 (+6.4 points, own evaluation). RPO and IPO were not confirmed by search.
- **Step-level vs trajectory-level evidence.** Step-DPO argues DPO on whole solutions "has shown limited benefits" on long math chains, with no numeric comparison in the abstract. IPR's appendix shows an ETO error that a step-level method corrected, one case only. This is weak evidence.

## Five recommendations (ranked)

1. **Branch-point choice: suggested.** Keep your confident-fork rule but add a second filter: fork only where the user turn or tool result is deterministic given the prefix, or where the chosen and rejected actions are both tool calls with different arguments. This avoids branches whose outcome is decided by the user simulator's randomness. Agentic-DPO and ToolGraph both match states across trajectories, which is the same idea. Untested for your setup.

2. **Rollouts per branch: suggested.** Run at least 4 rollouts per branch for both the chosen and the forced runner-up. Count a pair as "differs" only when the outcome gap is at least 3 of 4 on one side. Shown: none directly. The reason is that a single stochastic user simulator run is noisy. Untested.

3. **Loss: suggested.** Use DPO with an NLL or SFT term on the chosen branch (RPO-style), and monitor chosen-reward positivity as ToolGraph does. Stop when that metric falls below zero. Add a reference-free option (SimPO-style length normalisation) as a second arm. Shown only that SimPO helps over DPO in its own evals. The NLL term is untested for agents.

4. **Pair count: suggested.** Start with 150 to 300 fork pairs, the scale ToolGraph used, and check that the held-out reward moves. Scale toward Step-DPO's 10K only if the 300-pair result beats trajectory-level DPO on the same prompts. Shown: 161 pairs gave +0.051 on tau2 (ToolGraph). Untested for fork pairs.

5. **Control arm: suggested.** Compare against trajectory-level DPO and against SFT on the same successful traces, with the same prompt set. Fix pass marks before training: a win requires a gain on held-out tau2 retail tasks with a 95% bootstrap interval above zero. The falsifier is no gain over SFT after two iterations. Untested.

## Gaps

- Full texts of Step-DPO, IPR, ETO, and Agentic-DPO were not read. Numbers are from abstracts or summaries.
- No retrieved paper gives an entropy- or confidence-gated fork rule for agent DPO.
- RPO and IPO papers were not found by search.
