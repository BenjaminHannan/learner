# 68 — Relation alias table + canon (Exp 63 design)

Status: built, sealed, registered PASS (272/300 paraphrase with 0 wrong,
200/200 fabricated UNKNOWN, 230/230 dev agreement with 226/226 inverse
round-trip, coverage 518/521). Plain software only, no model at run time.

## Problem

Ears output open relation strings ("is the capital of", "was born in").
`scripts/fable_thought49_schema.py:suggest_relation_id` only matches the 521
WebRED names verbatim, and the reasoner hops by exact name, so every novel
phrasing becomes UNKNOWN and the hop abstains. Doc 58 (research) proposed a
frozen alias table + inverse table + UNKNOWN bucket; this doc is the build.

## Design

Three frozen JSON tables under `data/open/wikidata-props/`, built once from
CC0 Wikidata property data (labels, English aliases, P1696 inverse claims),
then read-only at run time:

- `alias_table.json`: normalised alias -> canonical WebRED name, only for
  aliases claimed by exactly one property (3,984 entries).
- `denylist.json`: normalised aliases claimed by > 1 property (243). These
  abstain — ambiguity never guesses.
- `inverse_table.json`: canonical name -> (inverse name, inverse pid) for
  declared P1696 pairs overlapping WebRED (76 relations), closed
  symmetrically so every edge round-trips.
- `missing.json`: properties 404 on Wikidata (["P450"], deleted/merged).

`canon(s) -> (name | None, pid | None, inverse_flag)` in
`scripts/fable_relcanon63_canon.py` (pure, deterministic, stdlib only):

1. Normalise (lowercase, strip, collapse whitespace).
2. Canonical-521 exact match wins (preserves today's behaviour; the denylist
   can never nuke a canonical name).
3. Denylist hit -> UNKNOWN.
4. Alias-table exact hit.
5. One rule pass: strip leading auxiliaries/articles ("is the X of" ->
   "X of"), then re-check. No stemming. Explicit exception list
   (follows/followed by, has part/part of) is looked up exactly, never
   transformed.
6. A trailing "(inverse)" / "[inverse]" or leading "inverse of " names the
   declared inverse of the base string (flag True) — this is how the
   reasoner traverses a stored hop backwards. Unresolvable -> UNKNOWN.
7. Everything else -> (None, None, False); the reasoner abstains and the raw
   string is logged for the next offline table round, never auto-promoted.

Where it plugs in: canon replaces the exact-match inside
`suggest_relation_id` (raw string still kept; id-less stays id-less), and the
inverse table extends the hop loop to traverse stored hops in either
direction. Taught facts are untouched; web text still never enters weights.

## Why tables, not a model (Ben's rule)

The target set is fixed (521 names), so a frozen human-readable table beats a
learned encoder: every mapping is inspectable, abstention is exact, and there
is nothing to install or gate. Learned proposers (CESI/AMIE/ESP per doc 58)
stay offline-only future work for proposing new aliases, which a human
reviews before they enter the table.

## Known quirks (source data, followed verbatim, not patched)

- Wikidata aliases mix perspectives: P40 child lists "mother of"/"father
  of"; P25 mother lists "son of"/"child of". Shared ones land on the
  denylist (correct abstain); unshared ones map as declared ("mother of" ->
  child). Test items avoid asserting against these quirks; they are listed
  in RESULTS.md instead of hidden.
- Noun-centric gap: verbal paraphrases outside the alias lists ("capital
  city of") abstain by design (28/300 in the test).
- Family inverses are undeclared on Wikidata (P22/P25 none; P40 -> P8810,
  outside WebRED), so father/child rows are agreement-only.
- P450 is gone from Wikidata (404); its relation keeps its canonical name
  but has no live property record.

## Tests (sealed before the run, one run)

300 hand-written paraphrases (5 templates x top-60 relations: verbatim name,
rule variants, Wikidata aliases, one natural verbal each) with gold names;
200 fabricated strings (nonce words + real-word distractors) that must be
UNKNOWN; dev.jsonl round trip on all 230 capital/capital-of/father/child
rows; coverage count reported without a bar. Marks in PASSMARKS.md with
SEAL.sha256.txt; predictions P63.1-P63.4 in the ledger before the run.

## What it means / What it does not mean

It means the assistant can now understand open relation phrasings with fully
explainable tables, abstain cleanly on anything ambiguous or unknown, and hop
backwards over declared inverses. It does not mean paraphrases outside the
tables resolve, that Wikidata's alias lists are semantically reliable, or
that any guessing was introduced anywhere in the pipeline.
