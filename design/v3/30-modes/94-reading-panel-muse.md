# 94 — Reading panel: hand-labelled TEST gold for the ears (Muse)

A labelled READING panel so the ears can later be scored on real simple-English text
(the reading ladder). Data build only: no training, no notebook writes, Mac CPU only.

## Source and attribution

400 sentences = `data/open/simplewiki86/heldout.jsonl` rows 0–399 in file order (2,000
held-out Simple English Wikipedia sentences). Text is CC BY-SA 4.0 + GFDL; attribution is
kept per row (`id`, `page`) and the licence/source recorded in
`data/open/simplewiki86/LICENCE.md`. Panel rows copy sentences mechanically (join by id);
only the labels are hand work. Nothing from this panel may enter any notebook or any
training input — it is a TEST panel (verified: no panel content referenced outside the
exp-86 extractor and exp-94 scaffold/scorer).

## Formats read

- Ears frame (`scripts/fable_ears47_data.py`): act in {STATE, ASK, RETRACT, UNSURE,
  NO_FACT}, relation from the class list, char-span subject/object, direction
  FORWARD iff subject starts at/before object. Panel triples map to STATE frames;
  NO_FACT rows map to NO_FACT frames.
- Inventory (`artifacts/fable-ears47-20260921/relation_classes.json`): 517 classes =
  481 WebRED-train relations ∪ closed-40 ∪ OPEN ∪ UNSURE. Crucially, the 40 held-out
  relations (author, cast member, position held, founded by, headquarters location,
  member of, league, location, official language, …) are NOT labellable — sentences
  stating only those get NO_FACT/relation-not-in-inventory.
- Thought row (`scripts/fable_thought62_schema.py`): read as reference only; panel rows
  are (subject, relation, object) + time/place qualifiers, convertible to thought rows
  later without writing any here.

## Labelling rules (frozen in sealed PASSMARKS.md, applied by hand to all 400)

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

## Double pass

The blind 80 (seed 94, drawn and sealed before labelling) were labelled FIRST, written
to `pass2.jsonl` before the 400-panel existed; the 400 were then judged fresh without
opening the pass-2 file. Result: exact triple-set 78/80, fact/no-fact 80/80,
kappa 1.0000; the 2 diffs are qualifier style only. Limitation: one labeller, one
session — this measures intra-labeller consistency, not inter-labeller truth.

## Outcome (integers)

155/400 sentences carry ≥1 triple (312 triples, 48 relations; located-in 137,
occupation 44, dob 37, dod 23, capital-of 8); 245 NO_FACT (177 relation-not-in-inventory,
60 vague-pronoun, 3 fragment, 3 list-or-table, 2 opinion). All four sealed predictions
(P94.1–P94.4) resolved TRUE. Full tables: `fable_reading94_RESULTS.md`, `fable_reading94_stats.json`.

## Questions for Ben

None. Most conservative defaults were taken throughout (documented per row in
`labeller_notes`); any future second labeller should re-label blind from these rules.
