# 132 — Question rewriter (Muse): relative clauses to canonical possessives

## Problem

On the sealed bench121 4-hop split, loop121 answers 136, abstains 63, wrong
1 -- and 62 of the 63 abstains are the loop's own "I didn't understand that".
Dev census on the two seen 4-hop splits (400 items, fresh loop121 notebooks)
shows three mechanical classes behind the abstains: (A) intact chain walk
with a cue gap (~35/400: "head coach" for the taught-as-officeholder hop,
"calls home"/"is home to" for citizenship, "faith"/"adheres" for religion,
"performance" for performer); (B) island walks (~55/400: "The R of X is Y"
teaches are stored as compound subjects -- "director of The Beatles", "head
coach of X", "origianl broadcaster of X" with relation officeholder -- so
the plain walk stops after a prefix or finds no entity); (C) unfixable
question-side (~16/400: loop-guarded repeats, teach gaps).

## Design (one change)

`scripts/fable_qrewrite132.py` exports `rewrite_question(question, triples)`:
resolve the question's nested descriptions against the notebook (verbatim
entities; compound subjects by prefix/target decomposition with
origianl→original typo normalisation; single-outgoing triple hops, hopping
islands via string containment with prefix words evidenced in the question),
walk the resolved chain to the sink, require every content word of the
original to be consumed (entity spans, relation cue phrases from the code
tables plus a small extended evidence map, or scaffolding), emit the
canonical nested-"of" form ("What is the <cue> of ... of <START>?"; the
canonical starts at the first island subject since the unchanged composer
cannot hop), and verify with the unchanged composers (exact frame, no
compound-subject hit). Exactly one verified candidate wins; otherwise the
input returns unchanged. No model, no downloads, deterministic.

`scripts/fable_loop132_agent.py` subclasses loop121: the exact base path
runs first; base asks return untouched (base correct answers stay correct by
construction); only base clarifies consult the rewriter, and the rewritten
turn goes through the exact base path again. Teach path, guards, fallback,
and all non-"?" turns are byte-identical to loop121.

## Evidence

Dev (seen splits): misunderstood 42→1 (bench103) and 62→1 (bench121), 0
correct→noncorrect, 0 new wrongs. Registered blind split (seed 132):
misunderstood 59→1 (drop 0.983), wrong 2 (both inherited teach-gap items the
base also asks wrong), 0 correct→wrong, 58 fixed. P2 64/64 rows identical to
base, P3 7/7, P4 30/30, redteam124 62/62 identical verdicts+reasons. Wave
40.4 s Mac CPU.

## Limits

Fixes only question-side parse failures. Teach-side gaps (unparsed
sentences, compound-subject chains the question never evidences, loop
repeats) still abstain or miss -- correctly, by abstaining rather than
guessing. The 14 redteam prefix-answer cases are inherited base behavior,
unchanged. Minimum 3 hops: 1–2 hop turns always keep the base path.

## Adapter notes (agents 3–7)

Question-side pre-filter only; notebook contract, reasoner, sleeper,
thinker, and mailbox protocols untouched. A rewritten ask carries the same
`(name, relations)` frame shape as a composer ask with stage
`loop132-rewrite`; downstream consumers need no change.

## What it means

Multi-hop phrasing coverage is now a question-side normalisation problem
with a verify-or-passthrough gate, not a model problem.

## What it does not mean

It does not teach, repair chains, or override guards -- anything uncertain
still clarifies exactly as the base loop would.
