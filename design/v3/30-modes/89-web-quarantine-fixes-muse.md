# 89 — Web-quarantine fixes for redteam79 (Muse, 2026-09-22)

Fixes doc-79 BUG-1 + the two UNCLEAR site-pairs, additively: the loop should
construct `QuarantinedThinking89` from `scripts/fable_webfix89_thinking.py`
(same `(notebook, searcher, fetcher)` signature). No existing file is edited;
all other `Thinking` methods are inherited unchanged.

## Fix 1 — None-like values dropped, never coerced

`_valid` is overridden: a claim whose value is `None`, a non-string,
empty/whitespace-only, or exactly `"None"`/`"null"` (trimmed, case-insensitive)
returns `"missing field"` before the copy-rule check. All other claims fall
through to the parent, so validity behaviour is otherwise identical.

## Fix 2 — registrable-domain 2-site rule

`_support`, `judge`, and `review` are copied with `_domain()` replaced by
`registrable_site()`: lower-case, strip port/trailing dots via
`urlparse().hostname`, strip one leading `www.`, collapse to last 2 labels (or
last 3 under a multi-part suffix). Built-in suffix list: co.uk, com.au, ac.uk,
org.uk, gov.uk, co.jp, com.br. Any non-ASCII host maps to a REJECTED site that
never counts toward the rule (seen-lists only, as `rejected.invalid`). So
sub.a.org+a.org, a.org:8080+a.org, and homoglyph pairs each count as ONE site
(and homoglyph-only pairs as ZERO) — never two. Residual: pure-ASCII
lookalikes still count separately.

## Evidence (sealed run, Mac CPU, fake pages only)

| check | result |
|---|---|
| X1 BUG-1 reproducer | kept=0, dropped=['missing field'], stored=[] PASS |
| X2 3 site-pairs | each 1 site (['example.org']), web-verified=0 PASS |
| X3 56 red-team cases | 55 OK + 1 RULE-CHANGED (RT79-43: seen-lists now read `example.org`; exclusion unchanged) PASS |
| X4 thinking selftest | 18 PASS before, 18 PASS through wrapper PASS |

Before-run reproduced doc 79 exactly (53/1/2), confirming the harness.

## What it means

Quarantine keeps its promises with tighter independence: empty/None junk never
stored, one operator cannot mint two sites via subdomain, port, or homoglyph.

## What it does not mean

Fake-page evidence only; ASCII-lookalike and rare-suffix gaps remain by design.
