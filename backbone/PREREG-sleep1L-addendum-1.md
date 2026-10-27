# Sleep-1L addendum 1 (2026-10-24 ~05:00Z, before any real run)
Implementation notes, no change to arms or marks:
- LoRA covers attention, short-conv and the dense MLP layers. The MoE experts and router get no adapter, to save memory on the
  32 GB Mac. Sleep-1 (Qwen 2B, dense) adapted every MLP. If S2 fails M1, this coverage difference is the first suspect.
- KL guard: the base model's top-32 log-probs are precomputed on the replay answers, and KL is taken over those indices.
- Thinking off: the assistant turn starts as `<think></think>`, and any think text is stripped before scoring.
