# GPT xhigh scout A — relatives of the transport/counter design (2026-09-21). Citations NOT yet verified by me.

The closest relatives support your core design choice: length-generalizing sequence algorithms work best when position/state representations encode the algorithmic relation itself, rather than ordinary absolute position. The two most promising changes are a signed/dense recurrent counter and sparse training-time reads.

A. Closest relatives

• “What Algorithms can Transformers Learn? A Study in Length Generalization” — 2024, ICLR. RASP-L’s central claim is that Transformers length-generalize when the correct solution has a short, length-independent program. Arbitrary index arithmetic is a bad fit; addition improves when corresponding positions are explicitly related and carry is externalized through an appropriate scratchpad. Try expressing each of your four clues as a uniform program and ablate any clue whose meaning depends on the training length. [ICLR Proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/45ed1a72597594c097152ef9cc187762-Abstract-Conference.html?utm_source=chatgpt.com)

• “Monotonic Location Attention for Length Generalization” — 2023, ICML. Relative forward/reverse location attention gives near-perfect extrapolation on copying/lookup, but simple relative attention breaks when the desired source-output displacement changes with timestep. This is strikingly close to your j−t and mirror-relative transport. Try replacing the hand-built clue set with a tiny learned location function, then test specially constructed variable-displacement tasks. [Proceedings of Machine Learning Research](https://proceedings.mlr.press/v202/ray-chowdhury23b.html?utm_source=chatgpt.com)

• “Randomized Positional Encodings Boost Length Generalization of Transformers” — 2023, ACL, arXiv:2305.16843. They identify unseen positional values as an OOD problem—even with relative encodings—and fix much of it by exposing short training sequences to randomized coordinates drawn from longer ranges; across 6,000 models/15 tasks this improved length-generalization accuracy by 12 points on average. Randomize the coordinate ranges seen by your transport clues during training; avoid letting n=64 introduce clue values never experienced at n≤12. [ACL Anthology+1](https://aclanthology.org/2023.acl-short.161/?utm_source=chatgpt.com)

• “Transformers Can Do Arithmetic with the Right Embeddings” — 2024, NeurIPS, arXiv:2405.17399; and “Position Coupling” — 2024, NeurIPS. Abacus encodes a digit’s position relative to its number; Position Coupling gives corresponding digit-significance positions the same ID. The latter trains on 1–30-digit addition and reaches 200 digits. For arithmetic, add a relation equivalent to “same significance in operand/output,” rather than global position. [arXiv+1](https://arxiv.org/abs/2405.17399?utm_source=chatgpt.com)

• “Functional Interpolation for Relative Positions Improves Long Context Transformers” — 2024, ICLR, arXiv:2310.04418. FIRE replaces a fixed relative-position table with a learned function plus progressive interpolation. Its evidence is long-context language modeling rather than your algorithmic setting, but it suggests testing a tiny continuous function over normalized relative clues instead of hand-picking/clipping every clue. [arXiv+1](https://arxiv.org/abs/2310.04418?utm_source=chatgpt.com)

• “DreamCoder: Bootstrapping Inductive Program Synthesis with Wake-Sleep Library Learning” — 2021, PLDI; “Bayesian Program Learning by Decompiling Amortized Knowledge” — 2024, ICML. DreamCoder learns reusable frozen-like program components and a search policy from few-example tasks during wake/sleep; the 2024 extension improves generalization when few solved examples exist. This supports your library-and-composition idea, but an exact published analogue of your frozen neural skill library + three-stage soft router learned from ~20 examples: not found. [PLDI 2021+1](https://pldi21.sigplan.org/details/pldi-2021-papers/55/DreamCoder-Bootstrapping-Inductive-Program-Synthesis-with-Wake-Sleep-Library-Learnin?utm_source=chatgpt.com)

B. Learning parity/counters reliably

• “Unlocking State-Tracking in Linear RNNs Through Negative Eigenvalues” — 2025, ICLR, arXiv:2411.12537. Positive-eigenvalue recurrent transitions cannot represent parity robustly in finite precision; allowing negative eigenvalues fixes parity, while modulo-3 requires richer/complex dynamics. For your counter, parameterize a 2×2 signed/orthogonal transition family capable of reaching −1 instead of initializing an unconstrained scalar recurrence near zero. Do not hard-code −1; make the useful dynamical family easy to discover. [arXiv](https://arxiv.org/abs/2411.12537?utm_source=chatgpt.com)

• “Parity Requires Unified Input Dependence and Negative Eigenvalues in SSMs” — 2025, arXiv:2508.07395. Merely putting input-dependence in one layer and negative eigenvalues in another still fails: the same recurrence must possess both. Make your counter transition token-dependent and signed within one module. [arXiv](https://arxiv.org/abs/2508.07395?utm_source=chatgpt.com)

• “On the Expressiveness and Length Generalization of Selective State Space Models on Regular Languages” — 2025, AAAI. Its SD-SSM uses a dictionary of dense transition matrices plus a learned soft selector and achieves perfect length generalization on several finite-state tasks. This is probably the most directly useful counter architecture for you: try 2–4 learned 2×2 matrices selected from the current symbol instead of one fragile counter recurrence. [AAAI Publications](https://ojs.aaai.org/index.php/AAAI/article/view/34301?utm_source=chatgpt.com)

• “Learning High-Degree Parities: The Crucial Role of the Initialization” — 2025, ICLR. Even ordinary parity learning changes dramatically with initialization: structured Rademacher initialization succeeds where sufficiently perturbed Gaussian initialization fails. Different setting, same warning: your 5/6 success rate may genuinely be an initialization problem. Compare orthogonal/sign-symmetric versus Gaussian initialization over many seeds. [ICLR Proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/31455446488c433ef29495ab44d4f53c-Abstract-Conference.html?utm_source=chatgpt.com)

C. Hard reads

The strongest length-specific evidence I found is not straight-through argmax but sparse attention: “Long-Context Generalization with Sparse Attention” — 2026, ICLR. α-entmax gives irrelevant positions exact zero probability; Adaptive-Scalable Entmax learns its sharpness and reaches up to 1000× extrapolation on synthetic tasks. Replace your softmax transport with entmax/ASEntmax during both training and testing before trying hard argmax. [ICLR Proceedings](https://proceedings.iclr.cc/paper_files/paper/2026/hash/19c9708f31ec44b5b1cbd67f91d05d95-Abstract-Conference.html?utm_source=chatgpt.com)

Direct evidence that straight-through argmax, Gumbel-Softmax, or entropy annealing specifically improves length extrapolation of pointer/transport reads: not found. I would therefore avoid making ST argmax the default until you benchmark it against entmax.

D. Carry

The best next task is LSD-first addition: input aligned pairs (a\_t,b\_t), maintain learned carry c\_t, output (a\_t+b\_t+c\_t) mod B, update c\_{t+1}, then emit the final carry. Train lengths 4–12; test 16/32/64/128, separately measuring no-carry, isolated-carry, and adversarial full-length carry chains. This isolates exactly one new capability—a two-state recurrent carry—while keeping transport/alignment simple.

“Neural GPUs Learn Algorithms” — 2016, ICLR, arXiv:1511.08228—learned binary addition from ≤20-bit examples and extrapolated to much longer inputs using recurrent convolutional computation; parameter-sharing relaxation, small dropout, and gradient noise helped training. RASP-L likewise finds addition substantially easier when output proceeds in carry-causal order, while Position Coupling supplies digit alignment. Use LSD-first order plus your learned counter rather than giving an explicit carry rule. [Google Research+2ICLR Proceedings+2](https://research.google/pubs/neural-gpus-learn-algorithms/?utm_source=chatgpt.com)

Ranked experiments

1. Run 30-seed parity experiments comparing your current counter against token-conditioned signed/orthogonal 2×2 transitions and an SD-SSM-style transition dictionary, measuring learned eigenvalues and extrapolation to length 512.
2. Replace transport softmax with α-entmax/ASEntmax and compare against softmax and straight-through argmax on the existing four skills through lengths 64–512, tracking support size and pointer entropy.
3. Add LSD-first base-10 addition with learned carry, train only at lengths 4–12, and stress-test to 128 digits with deliberately long carry chains.
