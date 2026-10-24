# Research: shared-prefix caching for LFM hybrid models, and LFM2.5-8B with thinking off (2026-10-24)

## Plain summary (for a high-school senior)
1. Each agent re-reads the same 4-10k-token "briefing" every turn; that costs 9-20 s on the 24B model.
2. We can read the briefing once, save the model's "memory of it" at fixed spots, and reuse it: first reply drops to about 1 s.
3. Keep the briefing's changing parts (notebook, chat) at the END, so the saved part stays valid.
4. The 8B model always "thinks out loud"; shutting the think box makes it write its planning as the answer (0/6 on the test).
5. Cheapest fix: let it think briefly (cap ~128 tokens) and hide that; a small retraining on our 1,792 chats is the backup.

Labels: SHOWN = in a source I read or in our own measurements; SUGGESTED = reasoned from sources/analogy; UNTESTED = my guess, needs our test.
Caveat: web search tool returned summaries; several sources are secondary. Verify against code before acting (CLAUDE.md rule).

## Part A: prefix cache design

### What other engines do
- vLLM: prefix caching for Mamba/hybrid is experimental. In `--mamba-cache-mode align`, recurrent state is stored only on a block grid, so a hit resumes only at a block boundary; an optional extra checkpoint at the end of a shared prefix exists (flag name differs by version). A Qwen3.5 report: block size 528, prompts shorter than one block got no hits. SHOWN (docs/issues).
  https://docs.vllm.ai/en/latest/features/automatic_prefix_caching.html
  https://github.com/vllm-project/vllm/issues/40696
- SGLang: MambaRadixCache = radix tree where a match returns the deepest node that holds a Mamba state; states are in-place, cannot be rolled back, are large, and reuse is "all or nothing"; KV evicted leaf-first, Mamba state from any node. Newer Unified Radix Cache (Aug 2026) keeps one token tree with attention KV and Mamba checkpoint as attached components; reuse boundary = deepest node every component accepts. SHOWN.
  https://pytorch.org/blog/hybrid-models-meet-sglang-more-than-full-attention/
  https://www.lmsys.org/blog/2026-08-11-unified-radix-cache
- llama.cpp: recurrent state is separate from KV; server keeps context checkpoints (`-ctxcp` default 32, `-cms` min step 8192, per one secondary blog, flags change between releases). LFM2 supported since PR #14620. Known bugs: discarded checkpoints force full re-prefill (#22746 cited). Frontends that hide the flags lose the benefit (LM Studio report: ~70-80 s vs ~1 s on 60k tokens). SHOWN (secondary).
  https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1818
  https://particula.tech/blog/prompt-reprocessing-swa-hybrid-models-kv-cache
- Common lesson across all three: conv/SSM state is valid only at the exact token position it was saved, so you must SAVE at chosen boundaries; you cannot trim back. SHOWN.
- mlx_lm: a PR proposing disk persistence of the LRU cache (`--prompt-cache-dir`, safetensors per entry plus manifest) was seen closed; merge status unknown. https://github.com/ml-explore/mlx-lm/pull/1405 . I could not find docs on ArraysCache trimming; our own finding (cannot trim) stands. Read `mlx_lm/models/cache.py` before building. UNTESTED.

### Recommended design (SUGGESTED, built on the above)
1. Prefill in segments and snapshot after each: S1 = system prompt, S2 = S1 + tool list, S3 = S2 + notebook. Snapshot = deep copy of all layers' cache (conv state arrays + KV for attention layers). Store keyed by hash of the exact token ids up to that boundary. Tokenize each segment so boundaries fall on token boundaries (end each segment with a fixed delimiter such as `<|im_end|>\n`, to avoid BPE merging across the seam).
2. Lookup: for a new request, find the longest stored boundary whose hash matches; load a COPY (never mutate the stored one); prefill only the rest.
3. Share across agents: S1 and S2 are identical for all agents of the same role, so one entry serves all. Make agent-specific content (role, notebook) come after the shared part. One process owning the cache (one server, or a cache dict in the agent runner) avoids duplicate memory; if agents are separate processes, use disk.
4. Disk: save snapshots with `save_prompt_cache`/safetensors, filename = model id + tokenizer hash + token hash. Reload cost is size/NVMe speed; the state is small relative to a full-attention model because only the GQA layers hold growing KV (estimate, UNTESTED: tens to a few hundred MB per 8k prefix, under 0.5 s to load). Invalidate on model, quantization or template change.
5. Notebook changes: layout is [system][tools][stable notebook][volatile notebook/recent notes][chat]. Edits to the notebook only invalidate S3 and later. Make notebook append-only between "compactions": append new notes at the end, and re-snapshot (cheap incremental prefill from S3) rather than re-prefill. Rewrite/compact only at sleep time, and re-prime then. Never put dates, counters, or "current time" in S1/S2.
6. Cap memory: keep S1/S2 pinned, LRU only for S3+ and chat snapshots. On 32 GB with a 24B-4bit (~13 GB) there is room for dozens of snapshots (UNTESTED).

### Expected TTFT savings (arithmetic on our measured speeds; actual UNTESTED)
- 24B-4bit at 420 tok/s: an 8k prefix costs ~19 s, 4k costs 8.7 s. With a full hit, only new tokens (say 300 chat tokens) are prefilled: ~0.7 s plus load time. About 10-25x lower TTFT.
- 8B-bf16 at 1000 tok/s: 8k prefix ~8 s -> ~0.3 s.
- Partial hit (notebook changed): only the notebook tail plus chat is re-prefilled; savings equal the share of the prefix before the change (system+tools often 30-50%).
- vLLM's align mode shows the caveat: hits are quantized to a block grid; our segment-boundary scheme loses nothing because boundaries are chosen, not gridded.

### First experiment A
Implement S1/S2/S3 snapshots in a standalone script (no server change), 24B-4bit, one 8k prefix, 20 fresh chat tails.
- Correctness pass: first 64 greedy tokens from cached path are identical to a no-cache run on all 20 tails (tolerate at most 1 of 20 differing at a late token from numerics).
- Speed pass: median TTFT with full hit <= 1.5 s (vs ~19 s baseline); with S3 invalidated (S2 hit) median TTFT <= 40% of baseline.
- Proves it wrong: any divergence in the first tokens (state copied wrongly or boundary tokenization mismatch), or load-from-disk TTFT above 3 s (then keep in-RAM only).

## Part B: LFM2.5-8B-A1B with thinking off

### What is known
- The card calls it a reasoning model: assistant turns contain an explicit chain of thought; it gives no way to turn thinking off, no budget parameter. Recommended sampling: temperature 0.2, top_k 80, repetition_penalty 1.05; the example uses max_new_tokens 8192. SHOWN.
  https://huggingface.co/LiquidAI/LFM2.5-8B-A1B
- The vLLM recipe: reasoning parser `qwen3`, tool parser `lfm2`, "do not cap max_tokens" because that truncates reasoning; trivial prompts may skip the think channel by themselves. No enable_thinking switch documented. SHOWN.
  https://docs.vllm.ai/projects/recipes/en/latest/LiquidAI/LFM2.5.html
- A third-party Core AI bundle forces an empty think block in the template and notes the model is always-thinking; it is a workaround, not an official mode. SHOWN (secondary): https://huggingface.co/visible-cx/LFM2.5-8B-A1B-CoreAI
- I found no Liquid doc recommending a no-think mode for the 8B or 24B. SHOWN (absence in what I could reach; the LFM docs site itself was not fetched).
- Why the leak is plausible: the model was trained to always put planning inside think; with an empty block the planning habit has nowhere to go, so it moves into the reply. SUGGESTED (consistent with our 0/6; not confirmed by any source).
- General: empty-think "NoThinking" works on models trained for hybrid modes (Qwen3, DeepSeek-V3.1) https://arxiv.org/pdf/2510.19176 . A secondary report says forcing thinking off costs up to ~10% on reasoning-heavy tasks. An anecdotal LessWrong comment says fine-tuning reasoning models on empty reasoning can badly degrade them. SUGGESTED / anecdotal.
  https://www.greaterwrong.com/posts/WmEcgcstzYCcMpc7z/your-model-organisms-might-be-fried/comment/dfj7LyabwBAjPyGti
- Our data: 24B-A2B in the same empty-think mode got 23/40, 8B-A1B 0/6 (n=6 is tiny). SHOWN (ours). Check whether 0/6 is leaked planning or wrong tool calls: read the transcripts first.

### Options ranked by cost (all UNTESTED on our setup)
1. Short think budget (e.g. 128 tokens): let it open `<think>`, stop at the budget, append `\n</think>\n` and continue; hide the think text from the user. Zero training, keeps its native format. Likely best first try. SUGGESTED.
2. Prefill the answer start: after the closed block, prefill the first tokens of the expected form (for a tool turn, `<|tool_call_start|>[`; for text, nothing leaks if we also ban the opening "The user"). Cheap, but only fixes turns where we know the form. Can combine with 1.
3. System-prompt instruction ("Answer directly; do not describe your plan; call a tool or reply to the user"). Cheap but weak when the template overrides habit; try as an add-on.
4. Zero budget (empty block) is the current failing baseline.
5. Detect-and-strip: reject replies matching planning patterns ("The user wants", "I need to") and re-sample with option 1. A safety net, not a fix.
6. Small LoRA/SFT on our 1,792 tool chats rewritten to `<think>\n</think>\n` + clean reply. Likely works, but risk of damaging reasoning (anecdote above) and costs a GPU run; do it only if 1-3 fail. Mix in some chats WITH short thinking to keep the skill.

### Recommended: option 1, then add 2 for tool turns; LoRA is the fallback.

### First experiment B
Run the same 6 tau2-retail tasks (plus 34 more to reach 40, same seeds as the 24B run) on the 8B-bf16, temp 0.2, three arms: empty block (baseline), 128-token budget, 128-token budget + tool-start prefill.
- Pass mark (fixed now): budget arm leaks planning text in <= 10% of visible replies AND solves >= 12/40 (30%; 24B gets 23/40).
- Proves it wrong: if leak rate in the budget arm is still > 50%, or score is <= baseline +2 tasks, then thinking placement is not the cause; stop and read the failures (maybe tool-format errors) before any LoRA.
- Change one thing at a time: baseline vs budget first; add prefill only if budget passes the leak mark but not the score mark.

## Cross-check list before acting
- Confirm `mlx_lm` cache.py behaviour for ArraysCache copy/save (not verified).
- Confirm llama.cpp flag names against its current README (blog-sourced).
- The 0/6 is a small sample; do not treat any of the above as settled.
