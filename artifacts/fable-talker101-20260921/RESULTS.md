# Exp 101 RESULTS — talker first-run prep + smoke tests (Muse)

## Result
PREP COMPLETE, both smokes PASS. The director can launch the full GPU run with one command (in the design doc). Nothing was trained except 200-update smokes; the full run does not exist yet.

## Marks table (counts, this run only, seed 101)
| Mark | Target | Got |
|---|---|---|
| S1 loss falls (CPU 200 upd, ctx128 bs2) | last-mean < first-mean | 7.161 → 5.496 PASS; val 7.4536 → 5.3516 |
| S2 ckpt/resume | 10%-ckpts exist, resume continues finite | ckpts 01–10 + last exist; resume 200→220, loss ≈5.35 PASS |
| GPU smoke (BensPC, 200 upd, ctx512 bs8 bf16) | runs only if GPU free | GPU free, ran: loss 8.44→4.22, val 4.2956, 15,000 tok/s PASS |
| Eval pipeline end-to-end (200-step ckpt) | val + 50 samples + BLiMP-10 print | val 4.2863/ppl 72.7, 50 samples, BLiMP-10 5247/10000 = 52.5% (chance-level, pipeline check only, NOT a result) |
| BLiMP word coverage | mostly in tokenizer text | 0 UNK of 278,859 tokens, 2.08 tok/word |

## Facts (all measured here)
- Data: SimpleStories/SimpleStories rev `e63b8adc…`, licence MIT, 2,115,696 train stories; val = sealed 1% (21,156 stories, seed 101, sha in `fable_talker101_split_info.json`).
- Tokenizer: 4096-token byte-level BPE fit on TRAIN ONLY (200k stories). Train 617,398,664 tokens (`train.bin` 1.23 GB), val 6,263,221.
- Model: 28,847,105 params (28.85M, in 25–35M band): 10 layers, d=512, 8 heads, RoPE, pre-norm, SwiGLU-1024, tied embeddings, ctx 512, pointer-generator copy head (0.52M).
- GPU: 1.66 GB peak at smoke batch; 16 GB card → full run fits easily at bs 32.
- Projection: 617.4M tokens / 15,000 tok/s = ≈11.4 h at smoke throughput; bigger batches run faster (launch-bound), expect 4–8 h.
- PASSMARKS sealed (`SEAL.sha256.txt` verifies OK) BEFORE any training; ledger P101.1–P101.4 written before the smokes.

## Deviations from my own plan
1. First smoke FAILED (loss ≈19, worse than uniform 8.32): two real bugs — targets were compared off-by-one AND default init made logits overconfident. Fixed (exact next-token alignment; GPT-2-style small init; p_gen bias +2 so training starts as ~pure LM). Re-ran: PASS. The fix is in the shipped scripts.
2. Smoke used `--warmup 20` (schedule compressed into the 200-step window); full run uses `--warmup 500`.
3. BLiMP repo ships NO licence file (checked) — eval use only, never training. Noted in PASSMARKS.
4. Eval `seq_logprob` scores vocab log-prob only (copy mass uncounted) — conservative for BLiMP, stated plainly.

## Exact reproduce (Mac)
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_talker101_train.py --device cpu --max-steps 200 --ctx 128 --bs 2 --lr 3e-4 --warmup 20 --seed 101 --out <dir>`
Full-run launch command: design doc `design/v3/30-modes/101-talker-first-run-prep-muse.md`.

## Questions for Ben
None. Default taken everywhere: single seed 101, bs 32 for the full run, BLiMP-10 paradigm list as in PASSMARKS.

## What it means
The pipeline is proven end to end: data, tokenizer, model, training, checkpointing, resume, and evaluation all run, and loss falls on both CPU and GPU.

## What it does not mean
No full training has happened — the smoke models are 200-update babies (BLiMP ≈ chance) and say nothing about final quality.
