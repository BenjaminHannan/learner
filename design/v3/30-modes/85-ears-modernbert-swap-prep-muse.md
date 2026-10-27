# 85 — Ears ModernBERT swap, PREP for the rung-2 wave (2026-09-21)

Status: prep complete, Mac CPU only. The 3-seed GPU wave is NOT run here; it
starts on the GPU the moment SciBERT's wave (exp 47) reports, with the command
at the bottom. New files only: `scripts/fable_ears85_train.py`,
`artifacts/fable-ears85-20260921/` (PASSMARKS + SEAL + RESULTS + smoke outputs).

## Why ModernBERT, why now

Doc 47c ranked encoders; ModernBERT-base (`answerdotai/ModernBERT-base`,
Apache-2.0, 149M params) is the scientific-vocabulary successor to SciBERT with
the same hidden size (768), and its plain-PyTorch loader is verified: exp 61
re-seal gives 40/40 token match, bit-exact hidden states vs the eager reference,
40/40 span coverage (the sdpa-vs-eager gap of 1.59e-3 is the reference
disagreeing with itself, recorded). Preparing the swap now means zero idle GPU
time later.

## What changed vs exp 47 (one thing only)

Encoder SciBERT → ModernBERT-base and tokenizer WordPiece → byte-BPE, via the
untouched `fable_modernbert58_loader.load` plus one additive line (`.d = 768`,
which the frame head reads). Unchanged: data pipeline (`encode_row`, panels,
golds, pool generators), frame head + loss, CAL golden-section temperature fit
(diff-clean vs 47 except a chunk-size parameter defaulting to 64), checkpoint
keys (`state/seed/temps/encoder_params/freeze_layers`), meta format, and all
wave flags. Recipe fixed: MAX_LEN 96, batch 32, bf16 on CUDA, AdamW 3e-5
cosine, 2 epochs, seeds 4701–4703.

## The pool problem and its fix

The 47 pool file stores SciBERT wordpiece ids — meaningless to another
vocabulary — so the wave cannot reuse it directly. `--build-pool` regenerates
the pool with the same generator functions and RNG stream but encodes with
ModernBPE (mirrors `make_pool`; rows tagged `"enc": "fable-modernbert85/1"`).
Length audit (E3): 4,085/140,903 pool sentences (2.899%, all long WebRED rows)
exceed 96 ModernBERT tokens; the build reports kept/dropped exactly as 47 did.

## Prep evidence (sealed beforehand, all Mac CPU)

E1: 20-step smoke (64 sents, width 22): loss 20.78 → 10.54, full-set eval
20.08 → 11.20; checkpoint reloads bit-identical; unchanged scorer functions
decode all 5000 cal rows (correct 435, 0 silent wrong writes — chance-level, as
allowed). E2: 149,350,418 params; ~2.84 GB bf16 estimate at batch 32/96 — fits
16 GB. Fixes found: restored 47's `@torch.no_grad` in the temperature fit (my
first copy dropped it → 14 GB spike, two SIGKILLs); smoke used cal-panel
sentences since pool rows lack re-encodable spans. P85.3 (< 1% over-long) came
out FALSE at 2.899% — recorded, harmless (truncation + span-drop at build).

## Exact GPU wave command (run on the GPU box, needs network once)

```
python scripts/fable_ears85_train.py --ensure
export SNAP=<printed snapshot path>
python scripts/fable_ears85_train.py --build-pool artifacts/fable-ears85-20260921/pool-modernbert.jsonl --snapshot $SNAP
for s in 4701 4702 4703; do python scripts/fable_ears85_train.py --seed $s --pool artifacts/fable-ears85-20260921/pool-modernbert.jsonl --snapshot $SNAP --cal artifacts/fable-ears47-20260921/panels/cal.json --out artifacts/fable-ears85-20260921/runs/m-$s; done
```

Only torch + numpy + huggingface_hub required (no `transformers`, per the
standing rule). The wave re-seals its own PASSMARKS before training; a small
85 scorer wrapper (same verdict code, ModernBERT loader) is still needed to
score it — flagged as follow-up, out of prep scope.

What it means: the swap is built, measured, and fits — the GPU can start
immediately. What it does not mean: no accuracy claim; the smoke model is
deliberately chance-level and no GPU step ran here.
