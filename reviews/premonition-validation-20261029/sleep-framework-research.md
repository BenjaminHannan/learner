# Sleep framework and Premonition

Google’s [October 27 overview](https://research.google/blog/the-sleep-framework-a-new-way-for-llms-to-retain-knowledge-in-continual-learning/) links [Language Models Need Sleep, v2](https://arxiv.org/pdf/2606.03979). The distinctive mechanisms are additional low-rank expert capacity, distillation on student-generated sequences, and synthetic practice selected for measured benefit. Earlier parameters remain frozen during consolidation; the full method includes routing and imitation-learning machinery.

Premonition currently updates one rolling LoRA. Its generic KL reference disables the adapter (`sleepmlx/torch_backend.py`), and optional continuation replay uses frozen-base answers. This protects base behavior on measured prompts; it does not establish retention of earlier personalized facts over many nights. Creative proposal scratch output is excluded from diary/training.

Our next tests, in order:

1. Measure three sequential fictional fact blocks, every earlier held question and untouched general questions. The authorized short control deliberately omits prior-fact rehearsal, so its outcome is a retention stress test rather than an exact reproduction of the full production night. Fix checkpoints and budgets before baseline.
2. Compare a teacher given verified source context against a student answering without that context. Measure learning and retention separately, keeping data exposure and compute comparable.
3. Compare a rolling adapter against a fresh residual trained while the incumbent stays frozen. Include a matched-rank control: extra capacity alone can change results. Combined factors require HF/native equivalence checks. Frozen old coefficients alone do not preserve output behavior.

These are proposed adaptations, not an implementation or reproduction of Google’s complete framework. Use synthetic data, bounded CPU resources and private artifacts. No production recipe, model or adapter changes follow automatically. The existing small tests show both learning and backend sensitivity; they are insufficient to establish continual learning.
