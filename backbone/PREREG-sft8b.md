# SFT-8B-1: does a small fine-tune on our tool chats fix the 8B's action mistakes?

Written 2026-10-24 before any training.

**Why:** LFM2.5-8B-A1B no-think scored 14/40 on tau2 retail in bf16. 22 of its 26 failures were wrong or missing write-call arguments, and every reply leaked planning text. At 4-bit it is fast enough for 4 agents (37.6 tok/s each).

**Setup:** official LiquidAI LFM2.5-8B-A1B-MLX-4bit, no-think template, on the Mac. QLoRA with mlx_lm.lora: rank 16, all layers, lr 1e-4, mask prompt (loss on assistant turns only), batch 1, 1 epoch over the first 900 chats of backbone/assistant_data/data/train.jsonl. Assistant turns are rendered with an empty think block, the way they are served. Hold out 100 chats of eval.jsonl for validation loss. No retail data is used in training.

**Arms:** Base = 8B q4 no-think (tau2 score from chain6). SFT = base + adapter.

**Primary metric:** tau2-bench retail, tasks 0-39, Haiku user/judge, 1 trial, no-think. Same harness as lfm25_8b_q4_nothink.

**Pass marks, fixed now:**
- P1: SFT ≥ base + 3 tasks.
- P2: leaked-planning replies drop by half or more (classify.py).
- If P1 passes, confirm with 3 more trials of both arms, and only claim a gain if the mean over 4 trials is ≥ base + 2.

**Proves it wrong:** SFT ≤ base, or SFT gains on leaks but loses on write-call arguments, meaning it learned the style but not the actions.

**Known noise:** 40 tasks × 1 trial has an SE of about 3 tasks, so a single-trial +3 is only suggestive.
