# RESULTS — Exp 63: relation alias table + canon (PASS)

Question: can open relation strings be mapped to WebRED's 521 canonical
names with plain software that abstains instead of guessing?

## Marks

| mark | bar | got | verdict |
|---|---|---|---|
| A1 paraphrase | >= 240/300, 0 wrong | 272 correct, 0 wrong, 28 abstain | PASS |
| A2 fabricated | 200/200 UNKNOWN | 200/200 | PASS |
| A3 dev round trip | 230/230 agree, 226/226 round-trip | 230/230, 226/226 (4 agreement-only) | PASS |
| A4 coverage | report only | 518/521 | reported |

Reproduce: `uv run --offline --no-project --python 3.12 --with numpy python -B scripts/fable_relcanon63_test.py`. Deterministic, no RNG, Mac CPU, seconds.

## What was built

`scripts/fable_relcanon63_build.py` fetched all 523 P-numbers in WebRED
frames from the Wikidata API (CC0, polite UA, 1 request per property, cached
under `data/open/wikidata-props/`). 522 fetched; P450 is HTTP 404
(deleted/merged), recorded in `missing.json`, not a failure. One 429
rate-limit forced a retry with a longer gap; no data was lost. Tables:
`alias_table.json` (3,984 alias -> canonical entries), `denylist.json`
(243 aliases claimed by > 1 property), `inverse_table.json` (76 relations
with a declared P1696 inverse overlapping WebRED), `missing.json` (["P450"]).

`scripts/fable_relcanon63_canon.py` is the pure function
`canon(s) -> (name, pid, inverse_flag)`: canonical-521 exact match first,
then denylist-abstain, then alias table, then aux/article stripping ("is the
X of" -> "X of") with an explicit exception list (follows/followed-by,
has-part/part-of). Anything else -> (None, None, False). The "(inverse)"
marker names the declared inverse (flag True) for backwards hops.

## Findings (all in the tables, verifiable)

1. Coverage 518/521 answers doc 58's "not computed". Uncovered: court,
   general manager, hardness (their own names collide across properties).
2. Wikidata aliases mix perspectives: P40 child lists "mother of"/"father
   of"; P25 mother lists "son of"/"child of". Shared ones correctly hit the
   denylist and abstain; unshared quirks ("mother of" -> child) are followed
   verbatim and documented, never hand-patched.
3. The 28 A1 abstains are all denylisted aliases ("written by", "owns",
   "succeeds") or unlisted paraphrases ("capital city of") — the noun-centric
   gap doc 58 predicted. Zero wrong mappings.
4. Family inverses are undeclared: P22/P25 declare no P1696; P40 declares
   P8810 (outside WebRED). So the 4 father/child dev rows are
   agreement-only; every declared pair round-trips (capital, follows,
   part/has-part, owner/owned-by, subsidiary/parent-org, ...).

## Deviations

Test items were picked from the alias lists with knowledge of the tables
(first verification already 272/0/28, so nothing was re-fitted after
sealing); A3 counts agreement-only rows separately as sealed. One run only.

## Questions for Ben

None. Default kept: ambiguous strings abstain rather than guess.

## What it means / What it does not mean

It means open relation strings now canonicalise to WebRED names with
explainable frozen tables, 0 wrong mappings on 300 paraphrases, 200/200
abstention on nonsense, and declared inverses that round-trip. It does not
mean unlisted verbal paraphrases resolve (28/300 abstain by design), that
Wikidata aliases are semantically clean (they are not — see finding 2), or
that father/child/mother have usable inverse declarations (they do not).
