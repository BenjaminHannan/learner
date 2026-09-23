# PASSMARKS — Exp 94 reading panel (TEST panel, data build, no training)

Written and hashed **before any labelling run**. Sealed: `shasum -a 256 PASSMARKS.md > SEAL.sha256.txt`.

Date: 2026-09-22 · artifact dir: `artifacts/fable-reading94-20260921/`
Data out: `data/open/reading94/panel.jsonl` (400 rows), `pass2.jsonl` (80 rows)
Source: `data/open/simplewiki86/heldout.jsonl` rows 0–399 (first 400, in file order),
CC BY-SA 4.0, attribution per row (`id`, `page`); see `data/open/simplewiki86/LICENCE.md`.
Inventory: `artifacts/fable-ears47-20260921/relation_classes.json` (517 classes).
Frame reference: `scripts/fable_ears47_data.py` (act/span/direction format).
Thought-row reference: `scripts/fable_thought62_schema.py` (never written to here).

## Registered labelling rule (fixed before sealing)
- Labeller reads each sentence by hand. No model calls, no auto-heuristics.
- Emit every (subject, relation, object) triple the sentence STATES whose relation
  string is exactly in the 517-class inventory, plus qualifiers {time, place} if stated.
- Else exactly one `no_fact_reason` in
  {fragment | relation-not-in-inventory | opinion | vague-pronoun-subject | list-or-table}.
- Conservative: no inference beyond the sentence; "American X" alone does NOT emit
  country of citizenship (emit occupation only when the job noun is present);
  "X is a town/city/province/district/municipality in Y" emits
  `located in the administrative territorial entity`; "X is the capital of Y" emits
  `capital of`; bare "X is a Y" (kind/instance) with no other inventory relation emits
  NO_FACT relation-not-in-inventory (`subclass of` is NOT claimed from bare "is a").
- Schema per row: id, page, sentence, triples[{subject, relation, object,
  qualifiers{time?, place?}}], no_fact_reason|null, labeller_notes.

## Marks (all integer counts, every case reported, never averaged)
- M1: panel.jsonl has exactly 400 rows, ids == heldout rows 0–399 in order. (PASS/FAIL)
- M2: pass2.jsonl has exactly 80 rows, random subsample seed 94, drawn before pass 2,
  written before any comparison. (PASS/FAIL)
- M3: agreement reported as integers: exact-triple-match count/80, NO_FACT agree count/80,
  fact/no-fact 2x2 table + Cohen kappa. No threshold — reported only. (PASS/FAIL on presence)
- M4: integer counts reported: sentences with ≥1 triple, triples per relation,
  NO_FACT by reason, 10 hard examples. (PASS/FAIL on presence)
- M5: NOTHING from this panel in any notebook or training input (verified by grep for
  panel ids in scripts/notebook dirs; 0 hits). (PASS/FAIL)

## Deviation log (append-only; none yet)
- none
