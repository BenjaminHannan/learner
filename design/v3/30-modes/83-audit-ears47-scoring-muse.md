# 83 — Audit of ears rung-2 scoring (pre-results, Muse, 2026-09-21)

Status: audit. Read-only: owns prefix `fable_audit83_`, folder
`artifacts/fable-audit83-20260921/`, this doc. The rung-2 wave trains on another
machine; this audit checks the scoring it will face before its results arrive.

## What was audited

The sealed contract (`artifacts/fable-ears47-20260921/PASSMARKS.md` + `SEAL.sha256.txt`),
the scorer (`scripts/fable_ears47_score.py`), the panel/pool builder
(`fable_ears47_data.py`), the head (`fable_ears47_model.py`), the trainer
(`fable_ears47_train.py`), all 10 sealed panels, `relation_classes.json`, and docs 47/59.

## Method

No existing file touched. Verification was by re-execution, not by reading alone: seal
hashes re-verified (12/12 OK) and content hashes recomputed (9/9 identical); panel sizes,
act splits, STATE counts, need_exec ceilings, class count (517), and unscorable counts
(0/0/0/0/0/13/0/11) all recomputed to integers; sentence/triple/entity overlaps computed
exactly between every test panel and the train pool's sources; a CPU dry run with
randomly initialised weights through the unmodified scorer proved end-to-end
executability and fixed the chance-level floor per mark.

## Findings (see RESULTS.md for the integer tables)

1. Scoring machinery is sound: every gated mark has a concrete computation; denominators
   match; CAL-only discipline holds for both temperatures and thresholds; the
   silent-wrong-write definition matches doc 47 and near-misses count as wrong; seeds are
   fixed for sampling, shuffling, init, and eval order.
2. Leakage is real but bounded and mostly in non-gated panels: wpos triples 813/1,806 in
   train (recorded only); wnewrel sentences 975/1,500 train-familiar with 0/1,500 triple
   and 0/40 relation overlap (gated — narrows the claim to relation-novelty, not
   sentence-novelty); wclosed 3/46 triples memorised; t_new×t_hard share 8 sentences.
3. The chance floor is ~0 (random weights execute nothing: 3-seed agreement plus the
   validator suppress all writes), so a future SAFE pass with ~0 EXECUTEs would be brake
   abstention, not learning — the coverage marks (SEEN/NEW/WEB) are the real gate, as
   designed.

## What this does and does not claim

- Does: the rung-2 scoreboard will measure what PASSMARKS says it measures, with the
  leakage qualifications recorded in `artifacts/fable-audit83-20260921/`.
- Does not: bless any future PASS — a PASS must still be read with the three rules in
  RESULTS.md ("What would make a PASS unconvincing"), and this audit never saw the
  trained weights.
