# 113c — Partial/prefix composer frames treated exactly like None (Muse, 2026-09-22)

For Ben in plain language: last time (exp 113b) the assistant learned to
hand confusing questions back to its old, careful self — but only when it
fully failed to understand them. The bug we found: sometimes it
half-understood a question (heard "citizenship" but missed "official
language", or ignored "in 2019") and then confidently answered the
shorter question it heard. This experiment adds one rule: a
half-understanding counts as no understanding — the question goes back to
the careful old path, which stays quiet instead of guessing. All 4 tricky
cases now stay quiet, and nothing else changed.

## The one change

`scripts/fable_loop113c_agent.py` (new, prefix-owned; nothing else edited).
`Loop113cEars` subclasses `Loop113bEars` and keeps 113b routing exactly,
except every non-None composer frame must also pass
`frame_consumes_question()` before it is asked:

1. **Qualifier test.** A trailing year qualifier ("in/since/until
`<year>`", "from `<year>` to `<year>`", "as of `<year>`", trailing "?"
allowed) means the frame is a prefix: loop102 never strips qualifiers on
questions, so no composer frame can consume one (fixes D8).
2. **Consumption test.** Delete every occurrence of the walked relations'
own mention cues, longest cue first, by substring (stems like "creat"
eat "created"; over-eating is the safe direction — it can only hide a
partial, never invent one). Then delete entity-name spans, longest first
("death" in "Death Eater" is a name, not a relation). If any OTHER
relation's cue still matches the remainder, the frame named fewer hops
than the question (fixes B7/C2 via "official language", C5 via "born").
3. **Conservative leftover matching.** Multi-word cues match by substring;
single-word cues match on word boundaries ("office" never fires on
"officer"); a small scaffolding denylist ("where", "city where/​located
where", "located", "situated", "home to"/"is home", "played"/"plays",
"speak"/"speaks"/"spoken", "work") never counts — these describe where a
walked hop happened or are shared across relations, and none is ever the
sole evidence of the 113b partial class.

A frame failing consumption delegates to the exact loop102 chain
(`Loop102Ears.hear` on the same instance), exactly as 113b does for
double-None — including the B73 explicit-2-hop branch. Compound-guard,
non-explicit clarify, hearsay screen, and the teach path are unchanged.
`scripts/fable_bench113c_run.py` runs loop113b-before and loop113c-after
on both splits with scorer v2; `scripts/fable_loop113c_marks.py` replays
loop102's P2/P3(L1–L6)/P4 marks against loop113c.

## Evidence (sealed P113c.1–P113c.4: 4/4 TRUE)

Registered run: split-A 200/200 right behaviour, 0 wrong, per-item
identical to 113b (M2 PASS); fresh 145 correct / 52 abstain / 3 wrong
(M3 PASS — correct meets the ≥140 bar exactly as in 113b, wrongs drop
5→3); P2 0 OK->BUG and 0 still-BUG with B7/C2/C5/D8 all OK, P3 L1–L6 all
pass (L6 200/200 × 3 seeds, L5-Z1 60/60), P4 30/30 with 0 false refusals
(M1 PASS); 52.7 s + 40.2 s (M4 PASS).

Exactly two items moved vs 113b, both improvements: fresh-125 and
fresh-200 (child-hop teach-gap partials whose B92 1-hop prefixes are now
delegated; loop102 clarifies, so wrong→abstain). The remaining 3 wrongs
(056/103/196) are mid-chain "and"-guard teach rejects with no notebook
evidence of continuation — out of scope as registered. A first gate
draft (substring-naive leftover scan) regressed 32 fresh items in
pre-seal scratchpad probes and was fixed before sealing; the registered
run was the first artifact run.

## Limits

The change is purely question-side routing; teach patterns, the 22
fresh-phrasing rejects, qualifier storage semantics, and the 3 remaining
teach-gap fresh wrongs are untouched. A partial the gate cannot see (its
leftover words are all scaffolding or entity names) keeps 113b behaviour
— the gate can only reroute toward loop102, never toward a new answer,
so it cannot invent a wrong the fallback did not already produce.

## What it means

Half-understood questions are now handled exactly like
not-understood ones: the N-hop composer answers only when its frame
accounts for the whole question, and the 113b M1 FAIL is fixed with zero
movement on anything the composer covers fully.

## What it does not mean

It does not mean the notebook knows more: where no evidence was ever
taught (056/103/196), the loop still answers from a partial frame when
the frame happens to consume the question — abstention there needs
teaching coverage, not routing.
