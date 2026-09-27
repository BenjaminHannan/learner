# Exp 97 — PASSMARKS (sealed BEFORE the registered run)

Independent test panel for the exp-63 relation-name canonicalizer.
Panel written blind: canon(), testdata, alias/denylist tables, and exp-63
test JSONs were never opened. Only inputs: the 60 canonical relation names
(+PIDs) and their plain Wikidata descriptions.

## Datasets (sealed alongside this file)

- `test_paraphrases.json` — 300 everyday-English relation phrases
  (5 per relation x 60 relations), each with gold canonical relation id.
- `test_fabricated.json` — 150 phrases naming no Wikidata relation,
  gold UNKNOWN for all.
- `test_nearmiss.json` — 50 dangerous near-misses (look like relation A,
  mean relation B, or mean nothing in the inventory), gold = correct id
  or UNKNOWN, with a `trap` note per item.

## Output normalisation (fixed now)

- The canonicalizer's raw output per phrase is coerced to a string
  (first element of a tuple/list, or the `relation`/`id`/`canonical`/
  `label`/`value` key of a dict), stripped, lowercased, with spaces and
  hyphens mapped to underscores.
- It counts as ABSTAIN iff the normalised output is in:
  `unknown, unsure, missing_fact, missing, abstain, abstained, none,
  null, n_a, unk, uncertain, cannot_tell, no_match`, or the raw output is
  None or the empty string.
- Otherwise the prediction is compared case-insensitively (underscores
  ignored) against the gold canonical name. Anything else is a concrete
  prediction: equal = correct, different = wrong.

## Marks (fixed now, do not change)

- K1 (paraphrases, n=300): WRONG <= 3 (rate <= 0.01). Correct and abstain
  counts reported, never averaged; every wrong reported verbatim.
- K2 (fabricated, n=150): UNKNOWN >= 147. Any concrete relation is a miss.
- K3 (near-misses, n=50): 0 wrong-direction predictions. Abstain is
  allowed and reported. Any concrete prediction != gold is wrong
  (a perspective flip counts as wrong). Every near-miss outcome reported
  verbatim (phrase, gold, raw output, verdict).

PASS = K1 and K2 and K3 all meet their bars. Abstain rate is reported,
never gated. One registered run only: a FAIL is recorded as FAIL.
