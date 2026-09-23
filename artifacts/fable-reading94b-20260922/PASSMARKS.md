# PASSMARKS — Exp 94b fresh reading panel (TEST panel, data build only; no training, no GPU, Mac CPU only)

Written and hashed **before any labelling run**. Sealed: `shasum -a 256 PASSMARKS.md > SEAL.sha256.txt`.

Date: 2026-09-22 · artifact dir: `artifacts/fable-reading94b-20260922/`
Data out: `data/open/reading94b/panel.jsonl` (400 rows), `pass2.jsonl` (80 rows)
Source: `data/open/simplewiki86/heldout.jsonl` rows 400–799 in file order (never rows 0–399),
CC BY-SA 4.0, attribution per row (`id`, `page`); see `data/open/simplewiki86/LICENCE.md`.
Inventory: `artifacts/fable-ears47-20260921/relation_classes.json` (517 classes).
Frame reference: `scripts/fable_ears47_data.py` (act/span/direction format).
Thought-row reference: `scripts/fable_thought62_schema.py` (never written to here).
Frozen procedure: `design/v3/30-modes/94-reading-panel-muse.md`,
`artifacts/fable-reading94-20260921/PASSMARKS.md`, `scripts/fable_reading94_build.py`
(mirrored as `scripts/fable_reading94b_build.py` with row range 400–799 and seed 9402).
Purpose: fresh panel for confirming exp 119f (designed from the exp-94 error analysis) on
sentences nobody has looked at. Nothing from this panel may enter any notebook or any
training input — it is a TEST panel.

## Frozen labelling rules (copied verbatim from the exp-94 doc, unchanged)

1. Emit every triple the sentence STATES whose relation string is exactly in inventory.
2. Conservative: no inference beyond the sentence. Pronouns/demonstratives/vague NPs
   ("It", "He", "This", "Billions", "the city", existential "There") with no
   in-sentence name → NO_FACT/vague-pronoun-subject, even when the page disambiguates.
3. Demonyms alone emit nothing ("American writer" → occupation only; no citizenship).
   Job nouns emit occupation. "X-born" emits place of birth X.
4. Admin-kind + in/of-PP ("town/district/province/municipality/city in/of Y") emits
   `located in the administrative territorial entity`, one triple per stated container.
   "Capital (city) of Y" emits `capital of`. Bare "X is a Y" emits NO_FACT
   (subclass-of never claimed).
5. Lifespan "(A – B)" / "born A" / "b.X/d.X" emits date/place of birth/death as stated.
6. Relation-specific: album/single from-or-by a band → performer; film year → publication
   date; "aired on" → broadcast by; "produced by (company)" → producer; "published by" →
   publisher; "passed by government" → legislated by; defeat/victory language never maps
   to winner; "developed by" is NOT manufacturer (developer is held-out); "run by" is NOT
   emitted (operator held-out); grandmother/grandson collapse to nothing (only
   mother/child/sibling/spouse emitted as stated, no chaining).
7. Qualifiers: explicit event dates attach as time; pass 1 carries no place qualifiers.
8. Exactly one NO_FACT reason: fragment | relation-not-in-inventory | opinion |
   vague-pronoun-subject | list-or-table.

Further frozen detail (from sealed exp-94 PASSMARKS.md, unchanged):
- Labeller reads each sentence by hand. No model calls, no auto-heuristics.
- Else exactly one `no_fact_reason` in
  {fragment | relation-not-in-inventory | opinion | vague-pronoun-subject | list-or-table}.
- Conservative: "American X" alone does NOT emit country of citizenship (emit occupation
  only when the job noun is present); "X is the capital of Y" emits `capital of`;
  bare "X is a Y" (kind/instance) with no other inventory relation emits NO_FACT
  relation-not-in-inventory (`subclass of` is NOT claimed from bare "is a").
- Schema per row: id, page, sentence, triples[{subject, relation, object,
  qualifiers{time?, place?}}], no_fact_reason|null, labeller_notes.
- Held-out relations (author, cast member, position held, founded by, headquarters
  location, member of, league, location, official language, …) are NOT labellable —
  sentences stating only those get NO_FACT/relation-not-in-inventory.

## Double pass (mirrors exp 94)

Pass 1: label all 400 rows fresh by hand. Pass 2: blind 80-row subsample (seed 9402,
drawn and sealed in `fable_reading94b_sample80_ids.json` before pass-2 labelling),
re-labelled fresh from the scaffold without opening the pass-1 file; then the exp-94
agreement/adjudication step (exact triple-set match, fact/no-fact 2×2 + Cohen kappa;
adjudicated panel is what ships). One labeller, one session: measures
intra-labeller consistency, not inter-labeller truth.

## Marks (all integer counts, every seed/case reported, never averaged)

- M1: panel.jsonl has exactly 400 rows, ids == heldout rows 400–799 in order. (PASS/FAIL)
- M2: pass2.jsonl has exactly 80 rows, random subsample seed 9402, drawn before pass 2,
  written before any comparison. (PASS/FAIL)
- M3: agreement reported as integers: exact-triple-match count/80, NO_FACT agree count/80,
  fact/no-fact 2x2 table + Cohen kappa. No threshold — reported only. (PASS/FAIL on presence)
- M4: integer counts reported: sentences with ≥1 triple, triples per relation,
  NO_FACT by reason, 10 hard examples. (PASS/FAIL on presence)
- M5: NOTHING from this panel in any notebook or training input (verified by grep for
  panel ids in scripts/notebook dirs; 0 hits). (PASS/FAIL)

## Registered predictions (ledger P94b.1–P94b.4, appended before the run)

- P94b.1: fraction of the 400 sentences with >=1 in-inventory triple lands in [0.25, 0.55]. 70%.
- P94b.2: the top NO_FACT reason is relation-not-in-inventory. 80%.
- P94b.3: exact triple-match rate on the blind 80 relabels >= 0.80 (64/80). 60%.
- P94b.4: Cohen kappa on fact/no-fact over the 80 >= 0.70. 60%.

## Deviation log (append-only; none yet)

- none
