# D5 - What this Mac can run (measured; times ET, 2026-10-08)

All rows below are **shown** (measured on this Mac, scripts in `scripts/`, raw numbers in `logs/D5-measurements.json`) unless marked.

| item | result |
|---|---|
| machine | 10 CPUs, 32 GiB RAM, 24 GiB free disk |
| python env | `/Users/ben-hannan/ucv4/venv/bin/python`: torch 2.11.0, transformers 5.17.0, MPS available |
| small transformer (4 layers, d=256, seq 64, batch 64, 11.6M params) | CPU 2.2 steps/s (8.8k tok/s); **MPS 5.0 steps/s (20.4k tok/s)** |
| FineWeb-Edu text | local shard `~/desmos-data/tok32k/fineweb_edu/tokens_0000.bin`: 19,999,782 tokens, 37,087 docs, ~86.6M characters. Decodes to clean English (200/200 docs round-trip exactly with the tok32k tokenizer under `desmos-llm`). |
| EmbeddingGemma 2 weights | `~/eg2/model.safetensors`, 1,488,915,288 bytes, sha256 matches the PC copy |
| EmbeddingGemma 2 loading | **blocked on transformers 5.17** (`embedding_gemma2` is not a registered model type; `eg.py` asserts >= 5.19). **Fixed**: `pip install --no-deps --target ~/tf519 transformers==5.19.0`, then run with `PYTHONPATH=/Users/ben-hannan/tf519` (main venv untouched). With it, `eg_ref.FrozenEG('~/eg2').load(...)` passes its own parameter-count check (271,002,624). |
| EmbeddingGemma 2 speed | embedding 256 short prompts (96 positions): **CPU 2.2 s, MPS 3.0 s** (first call, includes warm-up); load 3 s CPU / 7 s MPS; peak process memory ~3.3 GB. State shape [256, 96, 768]. |
| implication | The reader can run on this Mac. Precompute reader states once, cache to disk (one pass over a 30k-row sample is ~5 min; all 171,940 rows ~25 min on CPU, **suggested** from the 256-prompt timing), then train the thinker/talker on cached states. Small-model training on MPS is fast enough for a < 30 min wave. |

Not measured: bf16 behaviour on MPS (we use fp32 here; the model card warns about fp16 overflow). The PC GPU is busy with the G1 size test and stays untouched.
