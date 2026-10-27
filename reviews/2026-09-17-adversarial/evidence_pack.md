# COORDINATOR EVIDENCE PACK (inspected 2026-09-17)

Method: the coordinator fetched each source's arXiv abstract page and, where marked [HTML] or [ar5iv], the full text; the Nested Learning PDF was text-extracted locally. "Verified" means the title, authors, identifier and the quoted facts were read from the source. Nothing was re-run. Items marked [abstract] were checked only at abstract level, so method details beyond the abstract are not vouched for.

## Sources cited by RESEARCH_REVIEW.md

1. Schlag, Irie, Schmidhuber (2021). "Linear Transformers Are Secretly Fast Weight Programmers." arXiv:2102.11174, ICML 2021. [abstract] Establishes equivalence of linearized attention and 1990s fast weight programmers; proposes replacing "purely additive outer products by a delta rule-like programming instruction" so the FWP "can more easily learn to correct the current mapping from keys to values"; evaluated on synthetic retrieval, machine translation, language modeling. No lifelong or cross-sequence persistence evaluation.

2. Yang, Wang, Zhang, Shen, Kim (2024). "Parallelizing Linear Transformers with the Delta Rule over Sequence Length." arXiv:2406.06484, NeurIPS 2024. [HTML] Sec. 2.2: S_t = S_{t-1} - beta_t (S_{t-1} k_t - v_t) k_t^T, described as "a single step of SGD" on L_t(S) = 1/2 ||S k_t - v_t||^2. Sec. 4.1 synthetic: MQAR, MAD, RegBench. Sec. 4.2: 340M/15B tokens and 1.3B/100B tokens; a 3B run in Table 5. Sec. 5.3 limitation: DeltaNet "underperforms GLA due to its poorer state size scalability." State is per-sequence; no cross-sequence retention study.

3. Sun et al. (2024). "Learning to (Learn at Test Time): RNNs with Expressive Hidden States." arXiv:2407.04620. [HTML] Sec. 2.1/2.3/2.4: inner loss l(W; x_t) = ||f(theta_K x_t; W) - theta_V x_t||^2; W_t = W_{t-1} - eta grad l; W is reset to W_0 at the start of each sequence (learning is within-sequence only); mini-batch TTT with b = 16. Scales 125M-1.3B on the Pile and Books3, contexts 1k-32k.

4. Behrouz, Zhong, Mirrokni (2024/25). "Titans: Learning to Memorize at Test Time." arXiv:2501.00663. [HTML] Sec. 3.1: loss ||M_{t-1}(k_t) - v_t||^2; surprise = gradient; momentum S_t = eta_t S_{t-1} - theta_t grad l ("memory of surprise across time"); M_t = (1 - alpha_t) M_{t-1} + S_t with forgetting gate alpha_t. Sec. 3.3: "persistent memory" means learnable, input-independent parameters (task memory), NOT persistence across deployments. Models 170M-760M on 15B-30B tokens; RULER NIAH to 16K, BABILong. Whether memory state carries across separate documents is not stated explicitly in the fetched text; processing is segment-based.

5. Hartvigsen et al. (2023). "Aging with GRACE: Lifelong Model Editing with Discrete Key-Value Adaptors." arXiv:2211.11031, NeurIPS 2023. [abstract] Discrete local codebook of edits in a layer's latent space; base weights unchanged; "thousands of sequential edits using only streaming errors"; T5, BERT, GPT; measures edit retention, generalization to unseen inputs, locality.

6. Mitchell et al. (2022). "Memory-Based Model Editing at Scale." arXiv:2206.06520, ICML 2022. [abstract] SERAC: explicit memory of edits + scope classifier + counterfactual model; QA, fact-checking, dialogue benchmarks.

7. Todd et al. (2023). "Function Vectors in Large Language Models." arXiv:2310.15213, ICLR 2024. [abstract] A small number of attention heads transport a compact task representation; strong causal effects in middle layers; FVs can be summed to trigger new composite tasks. Pretrained autoregressive LMs only.

8. Hendel, Geva, Globerson (2023). "In-Context Learning Creates Task Vectors." arXiv:2310.15916, Findings of EMNLP 2023. [abstract] ICL compresses demonstrations into a single task vector theta(S) that modulates the transformer; pretrained models.

9. Ilharco et al. (2022). "Editing Models with Task Arithmetic." arXiv:2212.04089, ICLR 2023. [abstract] Task vector = fine-tuned weights minus pre-trained weights; negation, addition, analogy operations in weight space. (Distinct object from activation task vectors, as the review says.)

10. Dehghani et al. (2018). "Universal Transformers." arXiv:1807.03819, ICLR 2019. [abstract] Shared-weight recurrence over depth; ACT-style per-position dynamic halting; algorithmic tasks, LAMBADA, WMT14 En-De.

11. Geiping et al. (2025). "Scaling up Test-Time Compute with Latent Reasoning: A Recurrent Depth Approach." arXiv:2502.05171. [HTML] Sec. 3.1: prelude / recurrent core / coda; random initial state s_0; core takes (s_{i-1}, embedded input e). Sec. 3.3: recurrence count sampled from a log-normal Poisson during training; truncated backprop through only the last k = 8 iterations. Sec. 4: 3.5B parameters, 800B tokens, 4096 AMD MI250X (Frontier). Sec. 5.3: gains are task-dependent and saturate (HellaSwag near peak at 8 recurrences). Sec. 6.1: zero-shot adaptive exit when KL between successive latent states falls below 5e-4.

12. Jolicoeur-Martineau (2025). "Less is More: Recursive Reasoning with Tiny Networks." arXiv:2510.04871. [HTML] 7M parameters (5M Sudoku variant), 2 layers; answer state y and latent z; n = 6 inner recursions, T = 3 outer deep-supervision steps; about 1000 examples per task with about 1000 augmentations each; halting learned by a BCE-trained halt probability (the Q-learning continue loss was dropped); supervised on solved puzzles; no natural language; ARC-AGI runs "around 3 days with 4 H100"; 45% ARC-AGI-1, 8% ARC-AGI-2.

13. Graves (2016). "Adaptive Computation Time for Recurrent Neural Networks." arXiv:1603.08983. [ar5iv] Ponder cost rho_t = N(t) + R(t), P(x) = sum_t rho_t; loss L_hat = L + tau P(x); halting threshold 1 - epsilon with epsilon = 0.01; the paper states the network's behaviour "is quite sensitive to" the hand-chosen tau.

14. Banino, Balaguer, Blundell (2021). "PonderNet: Learning to Ponder." arXiv:2107.05407, ICML 2021 AutoML workshop. [ar5iv] Loss = sum_n p_n L(y, yhat_n) + beta KL(p_n || p_G(lambda_p)) with a geometric prior over halting; authors: "we don't regularize PonderNet to explicitly minimize the number of computing steps, but incentivize exploration instead"; the prior biases toward 1/lambda_p expected steps; inference samples a Bernoulli halt each step.

15. Rolnick et al. (2019). "Experience Replay for Continual Learning." arXiv:1811.11682, NeurIPS 2019. [abstract] CLEAR: on/off-policy mixture with behavioral cloning (V-Trace); Atari and DMLab tasks presented sequentially; "we do not provide an explicit indication to the model of task boundaries"; matches methods that require task identities; random discarding works for bounded buffers.

16. Burda et al. (2018). "Large-Scale Study of Curiosity-Driven Learning." arXiv:1808.04355. [abstract] Prediction error as intrinsic reward across 54 environments; random features often suffice, learned features generalize better; "limitations of the prediction-based rewards in stochastic setups" (noisy-TV).

17. Zelikman et al. (2022). "STaR: Bootstrapping Reasoning With Reasoning." arXiv:2203.14465. [ar5iv] GPT-J 6B; arithmetic, CommonsenseQA, GSM8K; rationalization gives the answer as a hint; each outer iteration fine-tunes "from the original pre-trained model M instead of continually training one model to avoid overfitting."

18. Zhao et al. (2025). "Absolute Zero: Reinforced Self-play Reasoning with Zero Data." arXiv:2505.03335. [HTML] Base models: Qwen2.5-7B, 7B-Coder, 3B-Coder, 14B, 14B-Coder, Llama-3.1-8B (all pretrained). Sec. 3.1 proposer reward: 0 if solver success rate is 0 or 1, otherwise 1 - success rate. Sec. 3.2: deduction / abduction / induction task modes; a code executor validates proposed tasks and verifies answers. Compute not stated. Sec. 6 / 4.2: "uh-oh moment" safety-concerning chain of thought observed with Llama-3.1-8B.

19. Zhang, Fu, Yan (2025). "MemGen: Weaving Generative Latent Memory for Self-Evolving Agents." arXiv:2509.24704v2. [HTML] Sec. 4.2 memory trigger: LoRA adapter; p_j = sigma(T_trigger(h_{t,1..j-1})); Bernoulli INVOKE/SKIP at semantic boundaries; RL objective with a reward-adaptive sparsity penalty lambda sum max(0, d - p_bar). Sec. 4.3 memory weaver: LoRA adapter on the frozen reasoner; generates K in {2,4,8} latent tokens from the reasoner's hidden states; latent memory prepended to the reasoner's hidden dynamics. Training: SFT (Eq. 11, App. B.1) or GRPO (Eq. 16, App. B.2); only weaver/trigger parameters update. Benchmarks: TriviaQA, PopQA, ALFWorld, AQuA, GSM8K, MATH, GPQA, KodCode, BigCodeBench; base models Qwen2.5-1.5B, SmolLM3-3B, Qwen3-8B. Sec. 5.3: post-hoc cluster-removal analysis interpreted as planning / procedural / working memory; claims stability on earlier tasks during continual learning. Note: MemGen's "memory" is the weaver's parameters trained offline on experience data, emitting per-query latents; it is not per-event online writes.

20. Behrouz, Razaviyayn, Zhong, Mirrokni (2025). "Nested Learning: The Illusion of Deep Learning Architecture(s)." NeurIPS 2025; arXiv:2512.24695; PDF at alibehrouz.com/files/NL.pdf (the review's abehrouz.github.io URL 301-redirects there). [PDF text] Sections: 1 Introduction; 2 Preliminaries; 3 Nested Learning (3.1 Associative Memory, 3.2 Nested Optimization, 3.3 Knowledge Transfer Between Levels); 4 Optimizers as Learning Modules; 5 Existing Architectures as Neural Learning Modules; 6 Takeaways; 7 Continuum Multi-Timescale Memory System (7.1 CMS, 7.2 CMS in optimizers / M3, 7.3 "Ad-hoc Level Stacking: Initializing CMS with Pre-Trained Models"); 8 Hope (8.1 Deep Self-Referential Titans, 8.2 training, 8.3 Hope module); 9 Experiments (9.1 continual learning and long context: class-incremental CLINC and others; "Continual Translation of a Novel Language" combining MTOB and Manchu with Hope-1/2/3 memory levels; 9.2 long-context models trained from scratch on about 50B tokens; 9.5 language recognition; 9.7 optimizers); 10 Conclusion. Sec. 10 states: "the undesirable phenomenon of catastrophic forgetting is not 'solved' in general" and calls forgetting "a natural consequence of compression." The review's "Sections 9-10" attribution is consistent with this structure.

21. Yan et al. (2025). "Memory-R1: Enhancing Large Language Model Agents to Manage and Utilize Memories via Reinforcement Learning." arXiv:2508.19828. [abstract] Memory Manager with ADD / UPDATE / DELETE / NOOP over an external store; Answer Agent with memory distillation; PPO and GRPO; trained on 152 QA pairs; LoCoMo, MSC, LongMemEval; 3B-14B models.

## Close precedents NOT cited by the review (coordinator-found)

22. Hu, Mitchell, Manning, Finn (2023). "Meta-Learning Online Adaptation of Language Models" (CaMeLS). arXiv:2305.15076, EMNLP 2023. [abstract] A small meta-model learns per-token loss weights for online gradient fine-tuning on document streams; it is meta-trained so that question answering AFTER one weighted gradient step improves; streams of thousands of documents; motivation: "the gradient signal from important tokens representing factual information is drowned out by the gradient from inherently noisy tokens." This is the closest published precedent to a learned writer for persistent weight updates trained through disjoint downstream queries.

23. Das et al. (2024). "Larimar: Large Language Models with Episodic Memory Control." arXiv:2403.11901, ICML 2024. [abstract] Kanerva-machine-style distributed memory matrix with least-squares one-shot writes/reads coupled to an LLM decoder; knowledge editing, sequential editing, selective forgetting, long-context; 8-10x speedups over gradient-based editors.

24. Wu, Wayne, Graves, Lillicrap (2018). "The Kanerva Machine: A Generative Distributed Memory." arXiv:1804.01756, ICLR 2018. [abstract] Memory matrix with linear-Gaussian Bayesian online updates (least-squares-like writes), learned addressing; Omniglot, CIFAR; greater capacity and easier training than DNC.

25. Munkhdalai, Sordoni, Wang, Trischler (2019). "Metalearned Neural Memory." arXiv:1907.09720, NeurIPS 2019. [abstract] Memory is a neural network; reading = pushing a key through it; writing = rapid parameter updates with meta-learned update rules; QA and maze RL.

26. Santoro et al. (2016). "One-shot Learning with Memory-Augmented Neural Networks." arXiv:1605.06065, ICML 2016. [abstract] Episodic meta-training where the label arrives one step after the sample, forcing store-then-retrieve inside an episode; content-based access. (Memory clearing between episodes is not visible at abstract level.) The proposed "teach, write, clear, query" contract is a within-episode variant of this protocol.

27. Miconi, Clune, Stanley (2018). "Differentiable plasticity." arXiv:1804.02464, ICML 2018; and Miconi, Rawal, Clune, Stanley (2019). "Backpropamine." arXiv:2002.10585, ICLR 2019. [abstracts] Hebbian plastic weight components with learned plasticity coefficients; Backpropamine adds a network-generated neuromodulatory signal that gates the plastic update, trained end-to-end; pattern memorization, Omniglot, maze RL, language modeling. Precedent for a learned, self-generated gate on weight writes.

28. Lin et al. (2025). "Continual Learning via Sparse Memory Finetuning." arXiv:2510.15103. [abstract] Product-key memory-layer models; update only memory slots highly activated by new knowledge relative to pretraining usage. Learning new facts: NaturalQuestions F1 drops 89% with full finetuning, 71% with LoRA, 11% with sparse memory finetuning at the same new-knowledge acquisition. A direct competitor design for persistent weight-based fact learning with low interference.

29. Wang et al. (2024). "MemoryLLM: Towards Self-Updatable Large Language Models." arXiv:2402.04624. [abstract] Fixed-size latent memory pool inside a transformer, self-updated with new text; model editing and long-context evaluations; "without any sign of performance degradation even after nearly a million memory updates."

30. Allen-Zhu, Li (2023). "Physics of Language Models: Part 3.1, Knowledge Storage and Extraction." arXiv:2309.14316. [abstract] Models trained on unaugmented biographies memorize but cannot extract facts via QA ("0% accuracy, regardless of subsequent instruction fine-tuning"); extraction requires augmentation (paraphrase, shuffling, translation) during pretraining.

31. Berglund et al. (2023). "The Reversal Curse: LLMs trained on 'A is B' fail to learn 'B is A'." arXiv:2309.12288. [abstract] Robust across model sizes and families; "not alleviated by data augmentation"; in-context reversal works. Weight-stored k -> v associations are directional unless the reverse is also written.

32. Ramsauer et al. (2020). "Hopfield Networks is All You Need." arXiv:2008.02217. [abstract] The modern continuous Hopfield update rule equals transformer attention; stores exponentially many patterns in the dimension. Contrast: a linear delta-rule matrix has capacity bounded by its rank.

33. Yang, Kautz, Hatamizadeh (2024). "Gated Delta Networks: Improving Mamba2 with Delta Rule." arXiv:2412.06464, ICLR 2025. [abstract] Adds a decay gate alpha_t to the delta rule: "gating enables rapid memory erasure while the delta rule facilitates targeted updates."

34. Graves et al. (2017). "Automated Curriculum Learning for Neural Networks." arXiv:1704.03003. [abstract] Learning-progress signals (prediction gain, complexity gain) reward a nonstationary bandit (Exp3.S) that selects tasks; can halve time to target performance.

35. Wang et al. (2022). "Self-Consistency Improves Chain of Thought Reasoning in Language Models." arXiv:2203.11171, ICLR 2023. [abstract] Majority vote over sampled reasoning paths, no oracle; GSM8K +17.9 points, SVAMP +11.0, AQuA +12.2.

## Coordinator math checks of RESEARCH_REVIEW.md
- grad_W 1/2 ||W k - v||^2 = (W k - v) k^T, so one SGD step is W + eta (v - W k) k^T. Correct.
- (W' - W) k' = eta (v - W k)(k^T k'). Correct; with unit keys k^T k' = cos(angle).
- eta = 1 and ||k|| = 1 gives W' k = v exactly. Correct.
- W = V K^+ solves W K = V when K (d x n, n <= d) has full column rank. Correct. Sequential delta updates are Kaczmarz projections: they converge for consistent systems; conflicting targets for the same key (corrections without decay) cycle rather than converge.
- Capacity: a d x d bank stores at most d exactly-recoverable associations with linearly independent keys. For random unit keys in R^48 the root-mean-square of k^T k' is 1/sqrt(48) = 0.144 and the mean absolute value is about sqrt(2/(pi*48)) = 0.115.
- 16 bytes per FP32 parameter with gradients and two Adam moments; 124M -> 1.984 GB; 700M -> 11.2 GB; 8 x 512 x 512 x 4 bytes = 8,388,608. All correct.
- If before/after score differences are zero-mean noise eps, E[max(0, eps)] > 0; for eps ~ N(0, sigma^2) it equals sigma / sqrt(2 pi). Correct.

## Draft-code facts confirmed by the coordinator (reviewers should still read the code)
- run.py passes hard = 10,000,000,000 and steady = 8,000,000,000 bytes to Budget when runtime.local.json omits hard_bytes/steady_bytes (it omits them), while storage.py's Budget.HARD/STEADY constants are 100 GB / 80 GB. The ledger's sampled peak is about 706 MB (registered read-only Python and wheel directories are counted).
- memorylab/experiment.py and a tests/ directory do not exist; run.py's training/evaluation entry points therefore cannot run yet.

## Addendum: Nested Learning pretrained-model adaptation (verified from the PDF text)
Sec. 7.3 ("Ad-hoc Level Stacking") initializes CMS blocks from pre-trained MLP blocks and notes that an internal learning rate near zero keeps the blocks at their pre-trained state. Sec. 9.1 uses Llama3-8B and Llama-3B as Hope backbones, applies the level-stacking technique, and follows with "continual pre-training with 15B tokens" (the ICL baselines get the same 15B-token continual pre-training). This supports the review's sentence that those experiments "include adapting pretrained billion-parameter models with substantial further training."
