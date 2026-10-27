# PASSMARKS — Exp 85: ModernBERT swap PREP for the ears rung-2 recipe (2026-09-21)

Written and hashed **before any exp-85 run**. This experiment PREPARES but does NOT run
the GPU wave: it builds `scripts/fable_ears85_train.py` (ModernBERT encoder under the
unchanged rung-2 recipe) and verifies it on the Mac CPU only. The 3-seed GPU wave itself
will seal its own PASSMARKS on the GPU machine before training.

Date: 2026-09-21 · artifact dir: `artifacts/fable-ears85-20260921/`
Prep under test: ModernBERT-base encoder (`answerdotai/ModernBERT-base`, Apache-2.0,
rev `8949b90`) via the verified `fable_modernbert58_loader.load` (exp 61: E2 bit-exact
vs eager PASS, E1 40/40 tokens PASS, E4 spans PASS, E5 pad-vs-single PASS; E3 vs sdpa
1.59e-3 exceeded the 1e-3 bar — recorded, reference-disagrees-with-itself).

## Prep marks (all Mac CPU, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1)

- **E1 CPU smoke:** 20 training steps on 64 pool-like sentences with tiny MAX_LEN 32,
  fp32, seed 4701: loss at step 20 < loss at step 1 (strictly decreases), checkpoint
  `ear.pt` written with the exact exp-47 key set
  (`state`/`seed`/`temps`/`encoder_params`/`freeze_layers`) + identical `meta.json`
  keys, reload gives bit-identical temps and matching head weights, and the unchanged
  `fable_ears47_score` decode path (`probs_for_model`, `decode`, `verdict_single`)
  runs on the reloaded checkpoint over the sealed cal panel and prints numbers
  (chance-level accepted; no accuracy bar).
- **E2 dry-run:** `--dry-run` prints total/trainable parameter counts and an estimated
  GPU memory budget at batch 32 / MAX_LEN 96 in bf16 with the formula shown
  (estimate, not a measurement; no bar beyond printing).
- **E3 tokenizer audit:** every sentence of the exp-47 training pool
  (`scratchpad/fable_ears47/pool.jsonl`, 140,903 rows, `text` field) is tokenized with
  the ModernBPE tokenizer at MAX_LEN 96; the count of sentences exceeding MAX_LEN is
  reported exactly (list included when short). Bar: a number is reported, whatever it is.

## What is fixed for the future GPU wave (not run here)

Recipe identical to exp 47 arm C: MAX_LEN 96, batch 32, bf16 autocast on CUDA,
AdamW lr 3e-5 cosine, 2 epochs, seeds 4701–4703, CAL temperature fit on the sealed
cal panel only, same checkpoint/meta format. Only the encoder + tokenizer change
(SciBERT WordPiece → ModernBERT byte-BPE). The wave re-seals marks before running.
