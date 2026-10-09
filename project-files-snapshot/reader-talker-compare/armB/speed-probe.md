# Speed probe, forward pass to last hidden state (no logits)

GPU: NVIDIA GeForce RTX 5090 (Vast offer 51027134, instance 54189184, Slovakia), torch 2.8.0+cu128, transformers 5.18.0, bf16, no_grad, warmup 3, median of 10.
Price $0.3756/hr. Total cost about $0.10-0.15 (about 10-15 min of rental plus one failed host, destroyed within minutes, instance 54188081, under $0.03).
Compile (reduce-overhead, batch 1, len 67): FAILED, no C compiler in the runtime image (skipped).
Hidden-state call: model.model(input_ids).last_hidden_state; truncation = slice layers + fix num_hidden_layers/layer_types.

| model | layers | params | emb params | batch | len | ms/forward | tokens/s | speedup vs full 1.2B |
|---|---|---|---|---|---|---|---|---|
| LiquidAI/LFM2.5-1.2B-Base | 16 | 1170M | 134M | 1 | 67 | 4.125 | 16242 | 1.00x |
| LiquidAI/LFM2.5-1.2B-Base | 16 | 1170M | 134M | 1 | 160 | 4.724 | 33866 | 1.00x |
| LiquidAI/LFM2.5-1.2B-Base | 16 | 1170M | 134M | 64 | 67 | 55.735 | 76935 | 1.00x |
| LiquidAI/LFM2.5-1.2B-Base | 16 | 1170M | 134M | 64 | 160 | 138.162 | 74116 | 1.00x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 4 | 396M | 134M | 1 | 67 | 1.063 | 63038 | 3.88x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 4 | 396M | 134M | 1 | 160 | 1.278 | 125214 | 3.70x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 4 | 396M | 134M | 64 | 67 | 13.888 | 308752 | 4.01x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 4 | 396M | 134M | 64 | 160 | 34.996 | 292603 | 3.95x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 6 | 524M | 134M | 1 | 67 | 1.493 | 44863 | 2.76x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 6 | 524M | 134M | 1 | 160 | 1.837 | 87093 | 2.57x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 6 | 524M | 134M | 64 | 67 | 20.718 | 206970 | 2.69x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 6 | 524M | 134M | 64 | 160 | 52.321 | 195716 | 2.64x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 8 | 659M | 134M | 1 | 67 | 1.867 | 35895 | 2.21x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 8 | 659M | 134M | 1 | 160 | 2.36 | 67783 | 2.00x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 8 | 659M | 134M | 64 | 67 | 27.729 | 154639 | 2.01x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 8 | 659M | 134M | 64 | 160 | 69.976 | 146336 | 1.97x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 10 | 787M | 134M | 1 | 67 | 2.272 | 29487 | 1.82x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 10 | 787M | 134M | 1 | 160 | 2.911 | 54961 | 1.62x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 10 | 787M | 134M | 64 | 67 | 34.823 | 123137 | 1.60x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 10 | 787M | 134M | 64 | 160 | 87.353 | 117226 | 1.58x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 12 | 914M | 134M | 1 | 67 | 2.734 | 24502 | 1.51x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 12 | 914M | 134M | 1 | 160 | 3.464 | 46188 | 1.36x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 12 | 914M | 134M | 64 | 67 | 42.088 | 101883 | 1.32x |
| LiquidAI/LFM2.5-1.2B-Base (trunc) | 12 | 914M | 134M | 64 | 160 | 104.836 | 97677 | 1.32x |
| LiquidAI/LFM2-350M | 16 | 354M | 67M | 1 | 67 | 3.892 | 17215 | 1.06x |
| LiquidAI/LFM2-350M | 16 | 354M | 67M | 1 | 160 | 3.848 | 41580 | 1.23x |
| LiquidAI/LFM2-350M | 16 | 354M | 67M | 64 | 67 | 18.409 | 232933 | 3.03x |
| LiquidAI/LFM2-350M | 16 | 354M | 67M | 64 | 160 | 44.316 | 231066 | 3.12x |
| LiquidAI/LFM2-700M | 16 | 742M | 101M | 1 | 67 | 3.508 | 19098 | 1.18x |
| LiquidAI/LFM2-700M | 16 | 742M | 101M | 1 | 160 | 3.494 | 45799 | 1.35x |
| LiquidAI/LFM2-700M | 16 | 742M | 101M | 64 | 67 | 39.91 | 107441 | 1.40x |
| LiquidAI/LFM2-700M | 16 | 742M | 101M | 64 | 160 | 87.936 | 116448 | 1.57x |
| HuggingFaceTB/SmolLM2-135M | 30 | 135M | 28M | 1 | 67 | 6.072 | 11034 | 0.68x |
| HuggingFaceTB/SmolLM2-135M | 30 | 135M | 28M | 1 | 160 | 6.074 | 26342 | 0.78x |
| HuggingFaceTB/SmolLM2-135M | 30 | 135M | 28M | 64 | 67 | 12.274 | 349368 | 4.54x |
| HuggingFaceTB/SmolLM2-135M | 30 | 135M | 28M | 64 | 160 | 26.014 | 393634 | 5.31x |
| HuggingFaceTB/SmolLM2-360M | 32 | 362M | 47M | 1 | 67 | 6.491 | 10322 | 0.64x |
| HuggingFaceTB/SmolLM2-360M | 32 | 362M | 47M | 1 | 160 | 6.473 | 24717 | 0.73x |
| HuggingFaceTB/SmolLM2-360M | 32 | 362M | 47M | 64 | 67 | 26.651 | 160897 | 2.09x |
| HuggingFaceTB/SmolLM2-360M | 32 | 362M | 47M | 64 | 160 | 54.364 | 188359 | 2.54x |
| Qwen/Qwen3-0.6B | 28 | 596M | 156M | 1 | 67 | 7.297 | 9181 | 0.57x |
| Qwen/Qwen3-0.6B | 28 | 596M | 156M | 1 | 160 | 7.364 | 21729 | 0.64x |
| Qwen/Qwen3-0.6B | 28 | 596M | 156M | 64 | 67 | 37.755 | 113575 | 1.48x |
| Qwen/Qwen3-0.6B | 28 | 596M | 156M | 64 | 160 | 90.715 | 112881 | 1.52x |
