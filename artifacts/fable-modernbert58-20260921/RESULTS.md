# RESULTS — fable_modernbert58: plain-PyTorch ModernBERT loader (2026-09-21)

Registered result: **FAIL** (sealed bar missed on M2 only). The loader itself is
bit-exact against the reference eager path; details below. Plain words for Ben:
we taught the computer to run ModernBERT with our own code, and it matches the
official code perfectly — but the official code has two slightly different ways
of doing attention, and our sealed promise was measured against the other one.

Snapshot: `answerdotai/ModernBERT-base` (Apache-2.0,
https://huggingface.co/answerdotai/ModernBERT-base), rev
`8949b909ec900327062f0ebf497f51aef5e6f0c8`. It was **not** in the HF cache, so per
the brief I downloaded it on the Mac only. Size stated before download (HEAD request):
`model.safetensors` 598,635,032 bytes (~571 MiB), `tokenizer.json` 2.1 MB,
`config.json`/`tokenizer_config.json` ~22 KB. Nothing was installed on BensPC.

## Marks (sealed in PASSMARKS.md, sha `f2ea788f…7da46e3f8277f43f`, before the run)

| mark | bar | measured | verdict |
|---|---|---|---|
| M1 token ids match reference | 20/20 sentences | 20/20 exact | PASS |
| M2 max last-hidden diff (fp32) | < 1e-4 | 3.07e-04 | **FAIL** |
| M3 one char span per token | 20/20 sentences | 20/20 | PASS |
| M4 `load()` wall-clock on CPU | < 60 s | 1.7 s | PASS |

Also: padded-batch vs single-sentence consistency 2.10e-05; 149,014,272 params loaded;
masked-LM head (`decoder.bias`, `head.dense/norm.weight`) skipped as designed.
Predictions: P234 TRUE, P235 FALSE, P236 TRUE, P237 TRUE (ledger).

## Why M2 failed (post-hoc probe, not a re-run)

The reference `AutoModel` defaults to the `sdpa` attention backend on this Mac.
A scratch probe (`scratch/probe_backend.py`) compared all three on the same 20
sentences: ours-vs-`sdpa` = 3.07e-04 (the registered number), ours-vs-`eager` =
**0.00 (bit-exact)**, `sdpa`-vs-`eager` = 3.07e-04. Worst gap on the longest
sentence (83 tokens). So the 3.07e-04 is the reference disagreeing with itself
across backends (kernel accumulation order over 22 layers), not a loader error.
My forward replicates the eager path exactly: fused Wqkv, NeoX-style RoPE
(theta 160,000 global / 10,000 local), GeGLU, pre-LN without biases, layer 0
with no attention norm, sliding window |i−j| ≤ 64 on non-global layers.

## Deviations

1. Reference compared with default backend, not pinned `attn_implementation="eager"`
   (the sealed command says `AutoModel.from_pretrained(snapshot)`; I kept it literal).
2. `str.isspace()` stands in for Unicode White_Space and L/N uses
   `unicodedata` categories instead of the `regex` crate tables in the
   pre-tokenizer; no check sentence distinguishes them (M1 20/20).
3. Added-token pre-splitting covers the snapshot's non-special added tokens only
   (space runs, `||IP_ADDRESS||`); literal `[CLS]`-style strings in user text are
   not split out (none in the check).

## Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy --with transformers python -B
scripts/fable_modernbert58_loader.py --check
$HOME/.cache/huggingface/hub/models--answerdotai--ModernBERT-base/snapshots/8949b909ec900327062f0ebf497f51aef5e6f0c8`
(check-total 3.8 s). New files only: `scripts/fable_modernbert58_loader.py`,
`artifacts/fable-modernbert58-20260921/`, `design/v3/30-modes/62-…md`. No commits.

## What it means / What it does not mean

It means we have a verified plain-PyTorch ModernBERT encoder: exact tokens,
exact eager-path states, per-token char spans for span pointers, 1.7 s CPU load.
It does **not** mean the sealed check passed — it failed on M2 as written, and a
FAIL stays a FAIL. A future re-seal could pin the eager backend or set the bar at
1e-3 (the BERT loader's bar); I did not re-run into a pass.
