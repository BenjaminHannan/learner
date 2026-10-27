# 101 — Talker first from-scratch run: prep + smoke tests (Muse)

Prep only. Ben approved the run 2026-09-21 23:40; the director launches the full GPU pass himself (the card runs one job at a time). Plan docs: 87 (30M decoder, 10 layers, d=512, 8 heads, 4k BPE + pointer/copy head on SimpleStories-EN) and 43 (mouth copy/fence locks — the copy head here is their pretraining incarnation: input = preceding context, pointer-sentinel style).

## What was built (prefix `fable_talker101_`, additive only)
- `scripts/fable_talker101_data.py` — carves sealed 1% val (seed 101) from the 7 train parquets; manifest with source URL, revision, licence, per-file hashes.
- `scripts/fable_talker101_tokenizer.py` — 4,096-token byte-level BPE on TRAIN ONLY (200k stories, seed 101); writes `tokenizer.json`, `train.bin`/`val.bin` (uint16), `token_counts.json`.
- `scripts/fable_talker101_model.py` — plain PyTorch (no `transformers`): decoder-only, RoPE, pre-norm RMSNorm, SwiGLU, tied embeddings, ctx 512, plus pointer-generator copy head (p_gen switch mixing vocab softmax with causal copy-attention scattered onto context ids). **28,847,105 params (28.85M).**
- `scripts/fable_talker101_train.py` — bf16 autocast on CUDA, AdamW, cosine+warmup, one pass, ckpts every 10%, val every 5%, resumable, JSON-lines log; flags `--device --max-steps --out` (+ctx/bs/lr/warmup/seed/resume).
- `scripts/fable_talker101_eval.py` — val loss/ppl; 50 continuations (10 fixed prompts × 5, temp 0.8, seed 101); BLiMP-10 minimal pairs by total log-prob, per-phenomenon rows.
- `artifacts/fable-talker101-20260921/` — PASSMARKS.md + SEAL.sha256.txt (sealed before any training), split manifest, tokenizer, shards, smoke logs/ckpts, RESULTS.md, `fable_talker101_full_run.bat`.

## Data provenance (measured)
SimpleStories/SimpleStories, `https://huggingface.co/datasets/SimpleStories/SimpleStories`, rev `e63b8adc3b1a1bdc7cac5b500d150b71346b0628`, licence MIT, 2,115,696 train stories (~275 words each). Val: 21,156 stories (1%, seed 101). Train tokens 617,398,664; val 6,263,221. BLiMP-10 from official repo alexwarstadt/blimp (no licence file ships with it — eval only, never training); 0 UNK over 20,000 sentences.

## Smoke evidence (seed 101, every case reported)
- CPU (Mac, ctx128 bs2): train 7.161 → 5.496, val 7.4536 → 5.3516 (S1 PASS); ckpts 01–10 + last exist; resume 200→220 finite ≈5.35 (S2 PASS).
- GPU (BensPC 5070 Ti, ctx512 bs8 bf16, GPU verified free first): loss 8.44 → 4.22, val 4.2956, p_gen 0.73 (copy head active), **15,000 tok/s**, peak **1.66 GB**.
- Eval validated on the 200-step ckpt: val 4.2863/ppl 72.7, 50 samples written, BLiMP-10 52.5% — chance-level as expected for a 200-update model; a pipeline check, not a result.
- First smoke attempt FAILED honestly (loss ~19): off-by-one target alignment + overconfident init; both fixed in the shipped scripts, re-run PASS. Recorded as a fixed bug, not a re-run into a pass (smokes are prep, not the registered run).

## The full run (for the director)
- One-line launch (log-written `.bat` already on BensPC; run only when `nvidia-smi` shows no other python):
  `ssh benspc 'cmd /c "cd C:\Users\benja\talker101 & start /b fable_talker101_full_run.bat"'`
  (the `.bat` runs `py -3.10 fable_talker101_train.py --device cuda --bs 32 --ctx 512 --lr 3e-4 --warmup 500 --seed 101 --data-dir . --out full_run` with stdout/stderr to `full_run.log`; re-login and check `full_run.log` + `nvidia-smi` to confirm it survived).
- Work: 617.4M tokens ≈ 37,700 steps at bs32×512. **Projected ≈11.4 h at measured smoke throughput (15k tok/s); 4–8 h expected** since the launch-bound small model gets faster per-token at bigger batches (1.66 GB at bs8 → bs32 fits easily in 16 GB).
- Gates (sealed): T1 final val ≥0.3 nats below 10%-ckpt val; T2 BLiMP-10 ≥70% per-phenomenon rows; T3 50 samples verbatim; T4 seed 101 only.

## What it means
Everything the full run needs exists, is staged on both machines, and has been proven to work; the only remaining step is wall-clock on the GPU.

## What it does not mean
No claim about the full run's outcome — T1/T2 are predictions (ledger P101), and a FAIL there stays a FAIL.
