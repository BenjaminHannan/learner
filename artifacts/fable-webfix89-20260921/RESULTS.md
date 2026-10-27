# RESULTS — Exp 89 web-quarantine fixes (2026-09-22)

Result first: all four sealed marks PASS. The fixed class stores nothing for
BUG-1, counts all three site-pairs as 1 site (believes none), leaves 55/56
red-team cases OK with the last one classified under a written rule, and the
thinking selftest is 18/18 before and through the wrapper.

## Integer summary

before (original Thinking): cases 56 | OK 53 | BUG 1 | UNCLEAR 2 (reproduces doc 79 exactly)
after (QuarantinedThinking89): cases 56 | OK 55 | BUG 1 (RULE-CHANGED, classified) | UNCLEAR 0
selftest: before 18 PASS / 0 FAIL, after 18 PASS / 0 FAIL (counts identical)

## Marks

| id | mark | bar | outcome |
|----|------|-----|---------|
| X1 | BUG-1 reproducer stores nothing | kept=0, dropped=['missing field'] | PASS: kept=0, dropped=['missing field'], stored=[] |
| X2 | three site-pairs = 1 site, NOT believed | RT79-09/-53/-11 web-verified=0 | PASS: sites all ['example.org'], n=1, verified=0 |
| X3 | 56/56 OK or classified with a written rule | 0 unclassified | PASS: 55 OK + RT79-43 RULE-CHANGED (below) |
| X4 | selftest count unchanged through wrapper | before == after | PASS: 18 == 18 |

## Changed pairs (4)

- RT79-18 BUG→OK: None value dropped before the copy rule (Fix 1).
- RT79-09 UNCLEAR→OK and RT79-53 UNCLEAR→OK: subdomain/port pairs now 1 site, unbelieved (Fix 2).
- RT79-11 OK→OK (obs changed to "homoglyph normalised"): cyrillic host REJECTED, pair = 1 site, unbelieved.
- RT79-43 OK→BUG, classified RULE-CHANGED (not a regression): the probe asserts
  the substring "a.example.org" in the look-elsewhere seen-list; seen-lists now
  carry registrable domains by design, so it reads "example.org". Exclusion
  still works (same domains passed, same cap behaviour); only the string form
  changed. Rule: seen-lists use the same registrable form as the 2-site count.

## What it means

The two red-team findings are fixed additively (no existing file touched) with
no behaviour change anywhere else: 52/56 cases byte-identical verdicts, the
selftest identical at 18/18.

## What it does not mean

Not a safety certificate: pure-ASCII lookalikes (paypa1) still count as
separate sites, and the suffix list is deliberately small (co.uk, com.au,
ac.uk, org.uk, gov.uk, co.jp, com.br); other multi-part suffixes fall back to
last-2-labels.

## Deviations

None. One sealed run, no re-runs. New files only:
`scripts/fable_webfix89_thinking.py`, `scripts/fable_webfix89_run.py`;
scratch used `scratchpad/fable_webfix89_rerun/` (redteam79 dirs untouched).

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_webfix89_run.py --out artifacts/fable-webfix89-20260921

Questions for Ben: (1) keep the small suffix list, or grow it later? (2) accept
pure-ASCII lookalikes as residual risk, or want a confusables table?
