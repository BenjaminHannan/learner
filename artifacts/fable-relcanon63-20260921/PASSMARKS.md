# PASSMARKS — Exp 63 (relation alias table, doc 68). Sealed BEFORE the run.

Registered command (from the repo root):

    uv run --offline --no-project --python 3.12 --with numpy python -B scripts/fable_relcanon63_test.py

Inputs (frozen, sealed with this file): `test_paraphrases.json` (300),
`test_fabricated.json` (200). No RNG anywhere: fully deterministic, one
process, Mac CPU. Code under test: `scripts/fable_relcanon63_canon.py` with
tables in `data/open/wikidata-props/` (built once from CC0 Wikidata data).

- A1 paraphrase: accuracy >= 240/300 AND 0 WRONG mappings (wrong = non-None
  output != gold; abstaining is allowed, abstains count as not-correct).
- A2 fabricated: 200/200 UNKNOWN, i.e. every one maps to (None, None, False).
- A3 inverse round trip: dev.jsonl rows with relation in {capital, capital of,
  mother, father, child} = 230 rows (114 + 112 + 0 + 2 + 2). ALL 230 must
  agree (canon output == gold relation + gold relation_id, flag False); the
  226 rows whose relation has a declared in-WebRED inverse (capital,
  capital of) must additionally round-trip both directions through the
  "(inverse)" marker. The 4 father/child rows have no declared in-WebRED
  inverse (Wikidata P22/P25 declare none; P40 declares P8810, outside WebRED),
  so they are agreement-only and counted separately, not round-tripped.
- A4 coverage: the count of the 521 WebRED names with >= 1 alias-table key is
  reported (build printed 518/521); no bar.

Overall: PASS requires A1 + A2 + A3 all met. A registered FAIL stays a FAIL.

What it means: these bars decide whether the frozen tables ship as the
run-time canonicaliser. What it does not mean: passing does not claim any
paraphrase outside the 300 will resolve, or that Wikidata aliases are
error-free (see RESULTS.md quirks).
