# 66 — ModernBERT eager reseal (experiment 61, Muse)

## Problem
Experiment 58 built a plain-PyTorch ModernBERT encoder that is bit-exact against the
reference *eager* attention path, but its sealed mark M2 was measured against the
reference default backend (`sdpa`) and registered FAIL (3.07e-4 vs 1e-4). That FAIL
stands and is never re-run. What is missing is a *new, cleanly registered* check that
pins both backends explicitly, on fresh sentences, so the loader's correctness claim
rests on a sealed pass rather than a post-hoc probe.

## Design
New file only: `scripts/fable_modernbert61_check.py` (prefix `fable_modernbert61_`).
It imports `load` from the 58 loader untouched and loads the reference twice
(`attn_implementation='eager'` and `'sdpa'`), all fp32 on CPU. 40 new sentences live
in the script: 20 scientific-abstract style (six long, targeting 80–120 BPE tokens,
exercising the 128-wide local sliding window across many positions) and 20 everyday
(contractions, numbers, punctuation, questions). None overlaps the 58 list, so this is
a genuine generalization sample, not a retest. `MAX_LEN=512` avoids truncation of the
longs; token ids are compared against `AutoTokenizer` with the same limit.

Marks: E1 exact token ids 40/40; E2 ours-vs-eager max diff < 1e-4 (the loader
replicates the eager path, so this should be near zero); E3 ours-vs-sdpa < 1e-3
(recorded — kernel accumulation order over 22 layers legitimately differs, as 58
showed); E4 char-span tiling 40/40, gaps whitespace-only, which is what span-pointer
ears need downstream; E5 padded-batch vs single < 1e-4, so batching is safe. Timing
(batch-1 and batch-16 ms/sentence) and peak RSS are reported with no mark to inform
ears-latency planning.

## Risks and deviations
`sdpa` on CPU must be available and deterministic; if it is not, E3 is reported as
measured with the backend string recorded rather than forced. Sentence token lengths
are targets (BPE fertility varies); the script prints the longest tokenized length so
the claim stays checkable. No training, no seeds, no BensPC use, no installs.

## What it means / What it does not mean
It means the 58 loader's eager-exactness claim gets a sealed, fresh-sentence test with
both reference backends named up front. It does not mean the 58 FAIL is overturned —
it stands — nor that ModernBERT is chosen for ears; that is a separate decision.
