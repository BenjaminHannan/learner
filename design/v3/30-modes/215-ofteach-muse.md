# 215 — Of-teach: "X is the R of Y" means "Y's R is X" (Muse)

## Problem

Director-verified on loop138i: `Sam is the boss of Kim.` and
`Lena is the mother of Theo.` are glued refuses; worse,
`Ada Pell is the composer of Blue Rain.` saves junk —
`Saved: Ada Pell's composer of is Blue Rain.` (relation `composer_of`,
subject/object swapped) — and later questions echo the junk. Exp 210
counted 26 such junk saves. Ben's rule: anything readable as a relation
should be read as one.

## Design: one parser change

New file `scripts/fable_loop215_agent.py` subclasses loop138i; the only
behaviour delta is an outermost ears mixin (`OfTeach215Mixin`, outside
ChainOf174) that rewrites the turn text, then lets the unchanged chain
hear the rewritten text — so write checks, multi-valued handling,
re-teach asks and corrections all run as before.

Teach rewrite (pure function `rewrite_teach215`): `X is the|a|an <mid>.`
-> `Y's R is X.`, where `<mid>` splits at the last ` of ` whose right
side is a name (`split_middle215`). Guards, each load-bearing in pilots:
R is 1–3 lowercase words with no clause/function words (closed
`_FUNCTION_WORDS215` set); Y is name-like (1–4 capitalised words) or a
known entity (one leading article may strip: `the Comets` -> `Comets`,
because the base only stores the article-free owner); never first-person
(`I am/is`), never article-less, never non-name Y (kills `best of
friends`, `last of five`, `talk of the town`, `one of the cities`),
never hearsay-shaped (whole-turn or attribution vocab in X), never
wh-word subjects (`What is the capital of Peru.`), never glued
(`?`/`!`/`;`/extra `.`) turns. Correction prefixes (`Actually, …`) are
preserved through the rewrite, verified live.

Question rewrite (`rewrite_question215`): `Who/What is the R of Y?` ->
`Who/What is Y's R?` only when the notebook already declares R (safe
gate; unknown R keeps today's reply byte-for-byte). The candidate is
probed: taken iff the base parses it as an ask (asks never write).

## Why subclassing is safe

`_act`, reasoner, notebook, sleeper, daemon are inherited untouched; the
loop class only swaps the ears. Multi-add re-entry (`_act_multi_teach`)
sees already-rewritten actions. Fictional names only throughout.

## Evidence

P1 40/40 (known + novel relations, incl. multi-word and article-Y names,
exact `(Y, R, X)` triples, 0 junk); P2 25/25 byte-identical; frozen
moves exactly the scan-predicted of-form set (rt136 14 junk→true;
rt143 3 reply-shape, 0 new wrong; sessions 0; bench 600 0; edit200 25
stale-gold rows; marks123 identical otherwise); reversal210 junk 26→0
with identical verdict tables; sleep smoke passes; seal 8/8 OK.

## Limits

No inverse inference is added (untaught direction still abstains).
Stale golds that reward the junk echo (25 bench65 `-fwd` rows, 14 rt136
cover triples) now score as moves; proposed upstream fix in RESULTS.md.
