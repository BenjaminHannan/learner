# PASSMARKS — experiment 61: ModernBERT eager reseal (sealed BEFORE the registered run)

Snapshot: `answerdotai/ModernBERT-base` rev `8949b909ec900327062f0ebf497f51aef5e6f0c8`
(cached on the Mac; no download, no network). Reference: transformers `AutoModel`
loaded twice, `attn_implementation='eager'` and `'sdpa'`. Ours: `load58` from
`scripts/fable_modernbert58_loader.py` (imported, not edited). Setting: fp32, CPU,
`MAX_LEN=512`, 40 NEW sentences in `scripts/fable_modernbert61_check.py`
(20 scientific-abstract incl. six 80–120-token longs, 20 everyday; none from exp 58).

| mark | bar | status |
|---|---|---|
| E1 token ids match `AutoTokenizer` | 40/40 sentences | sealed |
| E2 max last-hidden \|ours − eager\| | < 1e-4 over all 40 | sealed |
| E3 max last-hidden \|ours − sdpa\| | < 1e-3 over all 40 (recorded) | sealed |
| E4 per-token char spans cover text, gaps whitespace-only | 40/40 sentences | sealed |
| E5 padded batch-of-40 vs single-sentence max diff | < 1e-4 | sealed |

Recorded, no mark: CPU forward ms/sentence at batch 1 and at batch 16; peak RSS (MB).

Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy --with transformers python -B
scripts/fable_modernbert61_check.py
$HOME/.cache/huggingface/hub/models--answerdotai--ModernBERT-base/snapshots/8949b909ec900327062f0ebf497f51aef5e6f0c8`

Verdict rule: CHECK PASS iff E1–E5 all meet their bars. A registered FAIL stays a FAIL.
