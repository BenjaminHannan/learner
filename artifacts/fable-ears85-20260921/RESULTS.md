# RESULTS — Exp 85: ModernBERT swap PREP (Mac CPU only, 2026-09-21)

Plain words for Ben: the replacement brain for the ears (ModernBERT) is now wired
into the training recipe and tested on this Mac. When the current brain finishes its
run on your PC, this one can start immediately with one copy-pasted command.

## Marks (sealed in PASSMARKS.md, sha `53dba4f6…f0d6`, before any run)

| mark | bar | measured | verdict |
|---|---|---|---|
| E1 smoke: 20 steps, 64 sents, width 22, seed 4701 | loss step20 < step1, ckpt reloadable, cal scored | step1 20.7848 → step20 10.5383 (full-set eval 20.0755 → 11.1993); ckpt keys identical to 47; reload head+temps bit-identical; cal 5000/5000 decoded, numbers printed | PASS |
| E2 `--dry-run` params + GPU estimate | prints | 149,350,418 total (149,014,272 encoder + 336,146 head); est 2.84 GB @ batch 32 / 96 / bf16 → FITS 16 GB | PASS |
| E3 pool sentences over MAX_LEN 96 (ModernBERT) | report a number | 4,085 / 140,903 = 2.899% (all WebRED long rows; first 50 listed in `len_audit.txt`) | PASS (bar was "report") |

Cal-panel smoke numbers (unchanged scorer functions, single seed, chance-level as
allowed): n=5000, unscorable=0, correct=435, executed=0, echoed=0, rephrased=5000,
silent_wrong_write=0, tau_exec=0.5074. Every cal row encodable under ModernBPE.

## What was built

`scripts/fable_ears85_train.py` (new file, nothing else touched). Reused unchanged:
47's data pipeline (`encode_row`, panels, golds, pool generators), frame head + loss,
CAL golden-section temperature fit, checkpoint/meta format, and the verified
exp-58 ModernBERT loader (exp 61: bit-exact vs eager, 40/40 tokens). Only the
encoder + tokenizer are swapped. Wave flags identical:
`--seed --pool --snapshot --cal --out` (+47's `--epochs/--batch/--lr/
--freeze-layers/--steps-cap`), recipe fixed at MAX_LEN 96, batch 32, bf16 on
CUDA / fp32 on CPU, AdamW 3e-5 cosine, 2 epochs. New flags: `--ensure`
(one-time snapshot download for the GPU box), `--build-pool` (regenerates the
pool with the same generator + RNG but ModernBERT tokenization — required
because the 47 pool file stores SciBERT ids, meaningless to another vocabulary),
`--dry-run`, `--len-audit`, `--smoke`.

## Deviations / fixes found during prep

1. Smoke used 64 cal-panel synth sentences, not `pool.jsonl` rows (pool rows carry
   SciBERT ids + integer labels without char spans, so they cannot be re-encoded
   for a new vocabulary; same generator family as the pool).
2. The literal scorer CLI was not run (it hardcodes the SciBERT loader and a
   3-seed runs dir); instead its unchanged functions
   (`encode_panel/probs_for_model/decode/tau0_from_cal/score_panel`) decoded the
   reloaded smoke checkpoint. A GPU-side 85 scorer wrapper is still needed later.
3. Caught by RSS profiling: my first copy of `fit_temperatures` dropped 47's
   `@torch.no_grad` → 14 GB spike, SIGKILL ×2. Restored; logic now diff-clean
   vs 47 except an `infer_batch` chunk-size parameter (default 64 = 47).
4. `meta.json` is a superset of 47's keys (+`full_loss_before/after`, `smoke_max`).
5. Ledger P85.3 (< 1% over-long) is FALSE at 2.899%; the wave's `--build-pool`
   reports kept/dropped per split, same as 47's `make_pool` did.

## Exact reproduce (Mac, offline, cache present)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; export SNAP=$HOME/.cache/huggingface/hub/models--answerdotai--ModernBERT-base/snapshots/8949b909ec900327062f0ebf497f51aef5e6f0c8
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_ears85_train.py --dry-run --snapshot $SNAP
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_ears85_train.py --len-audit --pool scratchpad/fable_ears47/pool.jsonl --snapshot $SNAP
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_ears85_train.py --smoke --snapshot $SNAP --cal artifacts/fable-ears47-20260921/panels/cal.json --out artifacts/fable-ears85-20260921/smoke
```

## What it means / what it does not mean

What it means: the ModernBERT training path is real — same recipe, same
checkpoints, same scorer functions — and fits the GPU comfortably, so the wave
can start the moment SciBERT's wave reports.
What it does not mean: nothing about accuracy transferred — the smoke model is
chance-level by design, and no GPU step ran here.

## Questions for Ben

None. Default taken: GPU wave re-seals its own PASSMARKS on the GPU box before
training (this prep sealed only the prep marks).
