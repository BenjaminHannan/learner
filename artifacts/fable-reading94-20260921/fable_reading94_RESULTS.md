# RESULTS — Exp 94 reading panel (TEST panel, data build, no training)

Hand-labelled gold for scoring the ears on real Simple English text. Source sentences:
`data/open/simplewiki86/heldout.jsonl` rows 0–399 (CC BY-SA 4.0; attribution per row via
`id` + `page`; licence: `data/open/simplewiki86/LICENCE.md`). Inventory: the 517 ears
relation classes (`artifacts/fable-ears47-20260921/relation_classes.json`). One labeller
(me), reading every sentence; no model calls, no auto-heuristics. Pass 2 (blind 80) was
written BEFORE pass 1 existed; pass 1 re-judged all 400 without opening the pass-2 file.

## Files (new, this exp; nothing edited)

- `data/open/reading94/panel.jsonl` — 400 rows: id, page, sentence, triples[],
  no_fact_reason, labeller_notes. THE TEST PANEL. Never for training/notebook.
- `data/open/reading94/pass2.jsonl` — blind relabel of the sealed 80-sample.
- `data/open/reading94/fable_reading94_pass1_labels_p{1..4}.jsonl` — hand-label source.
- `artifacts/fable-reading94-20260921/fable_reading94_stats.json` — integer counts.
- `artifacts/fable-reading94-20260921/fable_reading94_RESULTS.md` — this file.
- `design/v3/30-modes/94-reading-panel-muse.md` — design + labelling rules.

## Marks (from sealed PASSMARKS.md; seal hash verified intact before labelling)

| mark | bar | result |
|---|---|---|
| M1 panel 400 rows, ids == heldout 0–399 in order | exact | PASS (400/400, order + sentences verified) |
| M2 pass2 80 rows == sealed seed-94 sample | exact | PASS (80/80 ids + sentences) |
| M3 agreement as integers (exact set, NO_FACT, 2x2 + kappa) | reported | PASS (see below) |
| M4 integer counts + 10 hard examples | reported | PASS (see below) |
| M5 nothing from panel in any notebook/training input | 0 hits | PASS (only refs: exp-86 extractor + exp-94 scaffold/scorer; no labels flow anywhere) |

## Counts (integers, every case, never averaged)

- Sentences with ≥1 in-inventory triple: **155/400** (38.75%). NO_FACT: **245/400**.
- NO_FACT by reason: relation-not-in-inventory **177**, vague-pronoun-subject **60**,
  fragment **3**, list-or-table **3**, opinion **2**.
- Total triples: **312** over **48** distinct relations. Top: located in the
  administrative territorial entity **137**, occupation **44**, date of birth **37**,
  date of death **23**, capital of **8**, place of birth **6**, performer **4**,
  part of **4**, population **3**, broadcast by **3**; 38 relations have 1–2 triples.
- Triples/sentence histogram: 0:245, 1:67, 2:34, 3:42, 4:9, 5:3.

## Agreement (blind 80; pass 2 written first, pass 1 judged without opening it)

- Exact triple-set match (subject+relation+object+qualifiers): **78/80**.
- Fact/no-fact agreement: **80/80**. 2x2: fact/fact 32, fact/nofact 0, nofact/fact 0,
  nofact/nofact 48. Cohen kappa (fact/no-fact): **1.0000** (po=1.0, pe=0.52).
- Jointly-NO_FACT with same reason: **48/48**.
- The only 2 diffs are qualifier style, same triples: Jalisco (pass2 place:"west" vs
  pass1 none) and Darwin capital-of (pass2 place:"Australia" vs pass1 none) — pass 1
  dropped place qualifiers per the frozen object rule.

## 10 hard examples (judgment calls, frozen rules)

1. Horus "god of the Sky…" → NO_FACT: deity role is kind, not occupation; no worshippers.
2. Mustafa III/succession → sibling kept; "Sultan" dropped (position held is held-out).
3. Saryan "Russian-born" → place of birth Russia (X-born rule).
4. Battle of the Allia / Sellasia defeats → NO_FACT: defeat language never maps to winner.
5. Perm "named Molotov, after Vyacheslav Molotov" → NO_FACT: subject "the city" unnamed.
6. Atharvaveda "one of the four Vedas in Hinduism" → religion Hinduism (text-tradition).
7. Scarface/Event Horizon "1983/1997 … movie" → publication date (film-year rule).
8. NTFS "developed by Microsoft" → NO_FACT: developer is held-out; no manufacturer stretch.
9. Handcuffs "often used by police" → used by police (named-kind generic subject allowed).
10. Saint Anna "mother of Virgin Mary and grandmother of Jesus" → mother only (no inference
    through Mary); Abigail Adams "wife of John Adams" → spouse.

## Reproduce (Mac CPU, offline; labelling itself is by hand)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \
  scripts/fable_reading94_build.py --agree   # recomputes exact/NO_FACT/kappa
shasum -a 256 artifacts/fable-reading94-20260921/PASSMARKS.md  # must equal SEAL
```

## Deviations

- D1: `panel.jsonl`/`pass2.jsonl` carry task/seal-fixed names (no prefix); all other new
  files use `fable_reading94_`.
- D2: single labeller, one session — agreement is intra-labeller consistency, not
  inter-labeller reliability; read kappa 1.0 accordingly.
- D3: object rule frozen mid-labelling (named entity; directional modifiers dropped; no
  place qualifiers in pass 1) — caused the only 2 pass diffs.
- D4: PASSMARKS, ledger P94.1–P94.4, scaffold, sample80 pre-existed from prior setup;
  seal hash verified matching before any labelling; predictions stood as sealed.

## Predictions (ledger P94.1–P94.4, sealed pre-run): all TRUE

P94.1 TRUE (155/400 = 38.75% in [25,55]). P94.2 TRUE (relation-not-in-inventory 177 top).
P94.3 TRUE (78/80 ≥ 64). P94.4 TRUE (kappa 1.00 ≥ 0.70). Brier: 0.09, 0.04, 0.16, 0.16.

## What it means / what it does not mean

- Means: the ears have a sealed 400-sentence TEST panel of real simple-English text with
  hand gold (155 fact, 245 NO_FACT) plus a measured 78/80 self-consistency reference.
- Does not mean: the ears can score well on it, or that the gold is inter-labeller truth —
  one labeller, conservative rules, and 177/400 sentences state no in-inventory relation.
