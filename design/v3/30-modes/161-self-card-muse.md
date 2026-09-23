# 161 — Self card: grounded self-answers (Muse, 2026-09-22)

## Problem

Loop138's self layer answered from a baked string table: fixed replies with
panel names written in ("Oslo and Paris are only values you taught me" even
when neither was taught; age replies naming one person; teach replies naming
one fact). The frozen router compounded it by firing only on panel wording,
so fresh names always declined. Five redteam probes caught the layer serving
panel strings on misses (see S5b moves).

## Change (one)

Replace the L2 answerer with SelfCard161 (`scripts/fable_selfcard161.py`):
`route(question)` maps to an intent with lowercase cue words plus
names/relations read from live notebook vocab (never literals), and
`answer_self(question)` builds the reply from live state (notebook rows,
event log, fact origins, turn log, counters, sleep history, filings).
`scripts/fable_loop161_agent.py` plugs it into loop138's L2 with the serving
rule unchanged (notebook wins; card only on miss; decline text on DECLINE).

## Grounding rules

- Second vs first person comes from the asked text (your/you = agent, my/I
  = user); all other names must resolve against the notebook.
- Content fires only when groundable: provenance/confirm need a live fact
  for the asked subject/relation; trail needs a walk ending in a plain
  value (mid-chain entity walks decline rather than overclaim a partial
  chain, e.g. bench103-s2fresh-006).
- Stance answers (opinions, feelings, favourites) need self-reference or
  entity-free text, so taught names in passing (song titles, "Happy Days")
  cannot hijack them.
- Counts need self nouns; "words"/"letters" and hypotheticals decline.

## Intent mapping

Route127 families map 1:1 to card intents (C1->count_facts …
C30->trail, D1->favourite … D10->dream, D8->username/identity by pronoun,
D9->age_you/age_me/age_them by pronoun, OOS->DECLINE); the table is frozen
in PASSMARKS.md.

## Evidence

S1 PASS (no panel names in code); S4 PASS (0/200 bench routed to content);
S5a exact (165 wrong→abstain, 599 identical); S2/S3/S5b FAIL with diagnosis
(matcher overfit dev phrasing families; 4 structural turn-path issues;
1 favorable verdict move). Full counts in RESULTS.md.

## Limits

Template matching keeps the same disease class as the router it replaces:
blind rephrasings ("recently", "who exactly are you", "treat as true",
"boundaries", packed ask+teach turns) still miss. The card never invents
names, but it can still answer the wrong intent — the next step is a
learned router over grounded answers, not more cues.
