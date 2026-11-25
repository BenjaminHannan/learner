# PROBLEM-7 ticket for the lead to relay to L1: 4-wide vs tall speed probe on the 5070 Ti (<= 12 min, read-only)

Timing only. No training to completion, no checkpoints kept, no data, no secrets. Nothing scored: this is the
measurement half of the shape race (accuracy half waits for family B, per Ben 11-23).

## Code
Folder to copy to the PC: `~/learner-ops/ds-copies/problem-7/shape-harness/` (scale/, vendor/, pc/).
It is the 5-scale-recipe harness (scale/ + vendor/ + pc/) byte-identical EXCEPT `scale/sizes.py`, which adds 2 lines:
`"Sw4": (384, 4), "Pw4": (1792, 4),` (4 blocks, matched total params; counts in PROBLEM-7/shape/counts.json).
- sizes.py sha256 `93d4c88fd875ead098d393cf1f13125fe4891daf9e14ce84386a153015db2ee0`
- per-file sha list: `ds-copies/problem-7/SHAPE-HARNESS-SHA256.txt` (its sha256 `213ae500...5b170`)
- py3.10 AST check: sizes.py, probe_all.py, train.py parse OK (Mac, feature_version 3.10).
- Mac smoke: `scale.train --size Sw4 --probe-steps 10` ran on MPS and CPU (EVIDENCE A4).

## Commands (from the copied folder; PYTHONIOENCODING=utf-8; PYTHONPATH=.;vendor)
Pass 1 (forward order):
`python -B -m pc.probe_all --sizes S,Sw4,P,Pw4 --arms default --batch 32 --steps 20 --precision bf16 --device cuda --out OUT\pass1 --total-cap-s 330 --per-probe-cap-s 150 --fallback-batch 16`
Pass 2 (reverse order, for drift):
`python -B -m pc.probe_all --sizes Pw4,P,Sw4,S --arms default --batch 32 --steps 20 --precision bf16 --device cuda --out OUT\pass2 --total-cap-s 330 --per-probe-cap-s 150 --fallback-batch 16`
Same flags as RESULT.md section 1 probes (bf16, batch 32, 4 ticks, K 1, default optimizer), so P tall can be checked
against the filed 1.686 s / 12.0 GB.
Guards: L1's usual RAM/commit/disk guards; whole card idle first. Return both `probe.json` files.

## Marks (filed before the run; speed only)
- Validity: P tall step within +/-15% of the filed 1.686 s (else the card state differs; report, no verdict).
- 4-wide FASTER at P: Pw4 step_s <= 0.67 x P step_s in both passes (>= 1.5x faster) at the same batch.
- 4-wide NOT faster: Pw4 step_s >= 0.90 x P step_s in either pass -> the overhead story (EVIDENCE A2/A5) is wrong.
- Between = PARTIAL. Memory: report train_peak_mib; Pw4 needing the batch-16 fallback while P does not = a memory cost
  to report (not a fail).
- My guess: FASTER 60% / PARTIAL 30% / NOT faster 10%.
