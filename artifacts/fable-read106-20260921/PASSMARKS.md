# PASSMARKS — Exp 106: first reading-ladder score (sealed before any inference)

Date: 2026-09-22 · dir: `artifacts/fable-read106-20260921/` · selector:
`scripts/fable_read106_score.py` (new file, prefix `fable_read106_`; imports
the sealed rung-1/rung-2 decoders read-only, never edited).
Test gold: `data/open/reading94/panel.jsonl` (400 hand-labelled held-out
Simple English Wikipedia sentences: 155 with >= 1 in-inventory triple,
312 triples over 48 relations; 245 NO_FACT). Inference only, Mac CPU,
no training, no notebook writes.

## 0. Fixed inputs (thresholds sealed by earlier exps, not chosen here)

- Rung-1 write gate = exp-76 certified tau-hat from
  `artifacts/fable-abstain76-20260921/ltt_summary.json`:
  tape 0.088756, bigru 0.30286 (same gate for all 3 seeds of each arm).
- Rung-2 write gate = each seed's own sealed tau_exec from
  `artifacts/fable-ears47-20260921/runs/report.json` (`tau_exec_single`):
  4701 → 0.9483702182769775, 4702 → 0.8766039311885834,
  4703 → 0.9547552053165873.
- Rung 2 is a registered FAIL; this exp is a measurement, not a re-test.

## 1. Scoring rule (fixed)

- One EXECUTE verdict whose item/frame act is a write act = one WRITE.
- Normaliser (all ears/seeds): casefold + strip + collapse internal
  whitespace on each of relation/subject/object; direction ignored; missing
  object → "". Correct write = normalised triple is a member of that
  sentence's gold triple set (counts once per write).
- Wrong write = a write whose normalised triple is NOT in the gold set for
  that sentence (includes EXECUTE RETRACTs: the gold has no retracts).
- 9 configs scored, every seed separately, never averaged:
  rung1-tape-4301/4302/4303, rung1-bigru-4301/4302/4303, rung2-c-4701/4702/4703.
- Rung-1 sentences past 8 distinct opaque toy-vocab words are unencodable
  (encoder returns None) → counted REPHRASE (unencodable), never a write.
- Neither decoder emits CLARIFY → reported as 0 with that note.

## 2. Marks

- **R1 (9 checks, GATED):** per ears/seed, wrong writes / writes ≤ 1%.
  0/0 passes vacuously and is labelled VACUOUS (not hidden).
- **R2 (9 checks, reported):** per ears/seed, correct writes / 312
  (recall; not gated).
- **R3 (9 checks, reported):** per ears/seed, writes on the 245 NO_FACT
  sentences (should be ~0; safety read only via R1).
- **R4 (reported):** per ears/seed, verdict counts (EXECUTE/ECHO/REPHRASE),
  raw act histogram, and the 10 most common wrong writes verbatim.

## 3. Predictions P106.1–P106.4 (ledger, before the run)

- P106.1 (0.85): all 6 rung-1 arm/seeds write 0 times on all 400 sentences
  (toy vocab + tau gate). Falsified by ≥ 1 write in any rung-1 seed.
- P106.2 (0.75): each rung-2 seed executes ≤ 5 writes total
  (tau 0.88–0.95 chokes output; exp 47 executed 0/46 on WebRED).
  Falsified by > 5 writes in any rung-2 seed.
- P106.3 (0.90): R1 gate PASSES for all 9 ears/seeds (wrong ≤ 1% of writes).
  Falsified by any R1 FAIL.
- P106.4 (0.80): recall (correct / 312) < 5% (≤ 15 correct) for every
  ears/seed. Falsified by any seed with > 15 correct writes.

## 4. Run rule

One registered run: `scripts/fable_read106_score.py --snapshot <scibert>`.
Mac CPU, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B …`. Checkpoints must load on CPU in < 10 min each or be skipped
(said so, no GPU). No re-runs into a pass.
