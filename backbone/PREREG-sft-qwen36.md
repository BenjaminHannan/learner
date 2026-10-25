# SFT-Q36-1: tool-chat fine-tune for Qwen3.6-35B-A3B (draft plan, 2026-10-25)

**Why:** Ben chose Qwen3.6-35B-A3B as the big-tier backbone (2026-10-25 13:40Z). On LFM the main failure was wrong IDs and arguments in write calls (22 of 26 failures for the 8B). This tests whether a small LoRA on our 1,792 tool chats fixes that on Qwen.

**Baseline first, no training:** tau2 retail 0-39, no-think (enable_thinking=False), Haiku user/judge, 2 trials, Qwen3.6 MLX 4-bit on the Mac, plus classify.py failure counts. If the backbone thread already has this, reuse it.

**Where to train (cheapest that works):**
- Option M, the Mac, free: mlx_lm.lora QLoRA on the 4-bit (~20 GB weights) with grad checkpointing and max seq 4096, against a 32 GB memory ceiling. Risk: OOM or about 30 s/iter, so 900 iters takes ~7-8 h and blocks the Mac.
- Option V, Vast RTX 5090 or A100, about $1-2: QLoRA in bnb NF4 on the HF weights with peft (rank 16, alpha 32, lr 1e-4, attention + shared-expert linears only, router and experts frozen). Merge into bf16, re-quantize to MLX 4-bit, and pull back (~20 GB). This matches Ben's "train the full-precision master, serve a re-quantized copy" plan.
- Recommendation: try Option M with a 20-iter smoke run to measure memory and speed. If it OOMs or takes over 15 s/iter, ask the coordinator to approve Option V.

**Data:** first 900 chats of backbone/assistant_data/data/train.jsonl in Qwen's chat template with tools, assistant turns only, an empty think block (no-think), and 100 eval chats for val loss. No retail data.

**Pass marks (fixed now):**
- P1: mean of 2 tau2 trials, SFT ≥ base + 3 tasks.
- P2: write-argument failures fall by at least a third.
- Wrong if SFT ≤ base, or if write-argument failures don't fall.
- Speed check: an adapter fused into the weights must keep tok/s within 5% of base.
