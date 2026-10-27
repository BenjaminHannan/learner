# PASSMARKS — fable_modernbert58 (ModernBERT plain-PyTorch loader) — sealed BEFORE the registered run

Registered run: `uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers python -B scripts/fable_modernbert58_loader.py --check <snapshot>`
with `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, on the Mac CPU, fp32, snapshot
`models--answerdotai--ModernBERT-base` rev `8949b909ec900327062f0ebf497f51aef5e6f0c8`.
Check sentences: the 20 `SENTENCES` in `scripts/fable_bert_loader.py` (reused verbatim).

| mark | statement | threshold | outcome that falsifies |
|---|---|---|---|
| M1 | Our BPE token ids equal the reference `AutoTokenizer` ids | 20/20 sentences exact | any sentence with any id mismatch |
| M2 | Our last-hidden states equal the reference `AutoModel` states | max \|diff\| < 1e-4 over all 20 sentences (fp32) | max diff >= 1e-4 |
| M3 | `encode` returns one char span per token (incl. `[CLS]`/`[SEP]`) | spans list length == ids length on all 20 sentences | any sentence where lengths differ |
| M4 | Snapshot loads on CPU quickly | `load()` wall-clock < 60 s | >= 60 s |

PASS = M1 and M2 and M3 and M4 all hold. A registered FAIL is recorded as FAIL, never re-run into a pass.
Seeds: none (deterministic loader; no training, no sampling).
