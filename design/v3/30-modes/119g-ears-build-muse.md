# 119g — relation-conditioned pointers + multi-fact decoding (ears build, Muse)

## Problem

119f proved data is not the bottleneck: 5,000 panel-shaped occupation rows
in training moved occupation exact from 0/44 to 0/44 (reading94) and 1/94
(reading94b), every seed, with gated writes 0/0/0. The director's frozen-weight
diagnosis (`artifacts/fable-ears119f-20260922/DIRECTOR-diagnosis.md`) names the
mechanism: the head's four span pointers (`ptr_q` in
`scripts/fable_ears47_model.py`) are fixed vectors shared across all 517
relations, so each sentence gets ONE fact slot. Real encyclopedia sentences
state 2-3 facts; the slot goes to the birth date or the nationality demonym,
and the occupation never survives. More single-slot supervision can only move
which fact wins — zero-sum. The fix must give each relation its own slot.

## Design (one change)

`scripts/fable_ears119g_model.py`: `RelCondEars(FrameEars)` with pointer
queries `q_r = ptr_q + U(rel_emb[r])`. `U` is a bias-free linear map
initialised to exactly zero, so at init `q_r == ptr_q` for every relation:
the new model is bit-identical to the old one (smoke proves max abs diff
0.0 across all five heads on 5 sentences). Training teacher-forces the gold
relation (`rel_override=batch["rel"]`); each pool row teaches its own
relation's pointers. New parameters: 517×64 embeddings + 64×(4×768) map
(≈ 230k, vs ~110M borrowed encoder). Everything else — encoder, pool,
recipe, seeds, taus, scorer marks — is 119f verbatim.

Decode (`scripts/fable_ears119g_score.py`): the act head is untouched (one
act per sentence). For STATE, candidate relations are the top-K calibrated
relation probabilities with p >= FLOOR (sealed K=3, FLOOR=0.10); each
candidate is decoded with its own conditioned pointers by a forced-rel frame
function that mirrors `S47.decode` line-for-line (same span rules, direction,
brakes 4/5, conf=min) except the relation is fixed and the confidence uses
that relation's own probability; verdicts are `S47.verdict_single` per frame
at the seed's tau. Duplicate triples are dropped. K=1 is always reported
with the verbatim old decode, so the K=1 column reproduces the 119f read.

## Why this should work

Each relation's pointers now train only on rows of that relation (occupation
pointers see 5,000 "PERSON was a DEMONYM PROFESSION" rows; date pointers see
date rows), so at decode time the occupation frame no longer competes with
the date frame for one slot — both can emit. U=0 initialisation means
training starts exactly from 119f behaviour and only diverges where the
gradient pushes, which bounds the downside: worst case the model re-learns
the single-slot solution. The FLOOR keeps the fan-out honest: relations with
<10% calibrated mass never emit.

## What could still fail

1. The training rows are all single-fact sentences, so the model never sees
   two facts co-occurring; the rel head may still put ~all mass on one
   relation per sentence (then K=3 degrades to K=1 and M1 fails).
2. Conditioned pointers may split mass across relations and hurt K=1 reads
   (M2 compares K=3 against the 119f K=1 bars 33/40/37, so regression shows).
3. Extra frames cost precision (M3 guards: within 0.10 of the step-0 119f K=1
   precision per seed) and could steal the occupation slot's neighbours
   (F1 slot-stealing falsifier on non-occupation exact vs 119f's 23/18/26).

## Marks and verdict

On sealed reading94b: M1 occupation exact ≥10/94 (3/3 seeds); M2 raw exact
(K=3) ≥33/40/37 positionally (3/3); M3 precision ≥ step-0 baseline −0.10 per
seed; M4 gated wrong-write rate ≤5% wherever writes exist. F1 voids the claim
on slot stealing. PASS = M1∧M2∧M3∧M4∧¬F1. W2b writes, gate47, and all of
reading94 are reported, not gating. Full bars, recipe, and the 40-minute
wall-clock plan are in `artifacts/fable-ears119g-20260922/PASSMARKS.md`.

## Staging closure (proved pre-seal)

The clean-folder import test initially failed exactly the way the 119f wave
once crashed: `fable_ears45_frames` (via 45_data) was missing, then
`fable_ears45_lexicon`, `fable_listening_m1`, `fable_notebook_contract`
(via the listening stack). The full transitive closure over `^(import|from)
fable_*` is 27 modules; all are in `scp119g.txt` and the clean import passes.

## Reproduce

Director stages via `artifacts/fable-ears119g-20260922/scp119g.txt` (closure
proved by a clean-folder import test), launches `wave119g.bat` detached on
BensPC (step 0 = 119f-baseline re-score; pool; 3 seeds; 47 panels; 94/94b ×
K=1/K=3), and fetches back `step0_119f.json`, `report47g.json`,
`taus119g.json`, four panel reports, `wave119g.log`, and three `meta.json`.
Mac smoke: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_ears119g_smoke.py --snapshot <scibert> --out
artifacts/fable-ears119g-20260922/smoke.json`.

What it means: each relation gets its own learned fact slot, ending the
zero-sum contest 119f diagnosed.
What it does not mean: no evidence yet that joint decoding beats the
single-slot baseline — the BensPC wave plus F1 decide that.
