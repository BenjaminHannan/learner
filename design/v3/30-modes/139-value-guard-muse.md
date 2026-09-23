# 139 — Value-span guard (Muse)

One-change fix for red-team-136 classes W3 (negation/hedge adverbs in values),
W5 (second-sentence tail) and W6 (compound "A and B" values): the teach value
span was stored raw even when it was not a single plain value. The fix is a
value-span validator applied to every teach path just before the write.

## The rule

On the value span AFTER the exp-129 punctuation strip, the turn does NOT
write and gets the loop's existing clarify reply (the exp-91 SPLIT message)
when the span:

(a) contains a negation/hedge word from a closed list fixed before any test
    (not, never, no longer, probably, maybe, perhaps, possibly, might,
    likely, i think; word-boundary, case-insensitive);
(b) contains a bare "and"/"or" joining two spans, unless the whole span is a
    member of the closed KNOWN_AND_NAMES list (benchmark golds with " and "
    plus Trinidad and Tobago, Bosnia and Herzegovina and three further UN
    member states) — so "Ann and Sue" refuses while "Trinidad and Tobago"
    stores exactly;
(c) contains a sentence boundary (". "/"! "/"? " + more text), where
    abbreviation periods do not count (preceding token abbreviation-shaped
    under the exp-129 rule, so "St. Louis" and "Apple Inc." store exactly).

## Where it sits

`ValueGuard139Mixin` (scripts/fable_fix139_valueguard.py) is cooperative, so
tonight's integration (exp 138) can stack it with sibling mixins: `hear()`
runs the base hear first (the exp-129 strip inside loop129b has already run)
and converts refused teach/correct actions to the existing clarify; `_act()`
re-checks strip-then-screen just before the write, covering the inner-chain
delegate path. loop139 = loop129b + mixin at both levels
(scripts/fable_loop139_agent.py, --daemon entry). Subjects, relation keys,
forget/ask/clarify paths untouched.

## Why this shape

The three classes share one root cause (no check on values,
fable_agent_loop.py:134) and one safe response (don't store what isn't a
single plain value; ask the user to rephrase). A validator at the write
boundary covers all four teach origins at once (bench73 patterns, exp-92
extra patterns, correction prefix, FakeEars possessive) without touching any
pattern. The closed lists keep the change falsifiable: anything not on them
behaves byte-identically to loop129b (verified per-item on all benches).

## Results (registered FAIL)

V1 probe 56/56 (0 wrong writes, 24/24 must-write exact); red-team-136 re-run:
the 7 focus cases now refuse, all 119 prior-OK stay OK, remaining 14
wrong-writes are other out-of-scope classes. BUT the closed and-name
allowlist (built from gold answers only) misses the bench teach value
"United Kingdom of Great Britain and Ireland": 11 fresh bench chains lose
that teach and answer wrong (4 old-s2fresh + 7 new-121), so V3 FAILs, and the
wave also missed the time bar (V4 FAIL). Do not integrate this version; the
and-rule needs a new experiment (e.g. allow multi-token spans, or source the
list from teach values). See artifacts/fable-fix139-20260922/RESULTS.md.

## What it means

Teaches that deny, hedge, pack two facts, or append a second sentence no
longer silently corrupt the notebook; ordinary values (including and-names
and abbreviations) store exactly as before.

## What it does not mean

It does not fix the remaining 136 classes (officeholder chit-chat, emoji
tails, trailing quotes, abbreviation dots) and does not judge truth — a
confidently-stated false single value still stores.
