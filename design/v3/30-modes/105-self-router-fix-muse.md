# 105 — Self-question router fix: scored routing with guards (Muse)

Exp 100 (registered FAIL) showed the exp-99 self-answerer is safe but
brittle: exact-substring routing declined 19 of 60 natural rephrasings
("taught" vs "teach", "hw many", contractions) and confidently misfired 5
times — "how many" questions answered with list content, and a belief
question answered "Yes..." with quarantine content. Exp 105 makes ONE
change (router only) and tests it on a 100-question panel written blind by
another agent.

## The one change

`scripts/fable_self105.py` subclasses the exp-99 agent and overrides ONLY
`answer_self()`'s routing. Answer bodies are inherited untouched: the
router picks an intent id, then calls the parent's answerer with that
intent's canonical exp-99 question (which provably triggers the same body
as exp 99). New text introduced: normaliser, keyword tables, guards, one
decline sentence. Routing stages, in order:

1. **Normalise**: lowercase; expand contractions ("can't"→"can not",
   "what're"→"what are", "where'd"→"where did"); fix "hw"→"how"; fold
   "can <you> not"→"cannot"; strip filler (so/um/like/ok/well/same) and
   bare "not" (negation lives in the cannot-fold); lemma map
   (taught/told/gave→teach, folks→people, slept→sleep, forgotten→forget,
   lives→live, corrections kept distinct from correct, etc.).
2. **Question-type guard** (before scoring; guarded-out ⇒ decline):
   "how many/how much/count/number of" ⇒ COUNT intents only (fixes the
   count-vs-list misfires); "why/how do you decide/what happens
   when" ⇒ process intents {C22,C23,C24,C25} or declines (fixes the
   correction-list trap); "believe" ⇒ C7 or decline (fixes the "Yes"
   misfire). Yes/no answers still come only from the inherited
   yes/no-from-state bodies.
3. **Keyword overlap scoring** with typo tolerance (edit distance ≤ 1,
   same first letter, both ≥ 3 letters).
4. **Margin + threshold**: best routes only if ≥ its threshold and ahead
   of the runner-up by a fixed margin of 2, else HONEST_DECLINE ("I have
   no record...", carries frozen decline markers).

## What tuning taught (dev: exp99-40 + exp100-80 only)

Two systematic traps, both fixed in the machinery rather than per
question. First, typo tolerance created false friends ("have"~"save"
gave every "have"-question +3 toward save-intents; "now"~"know"/"new",
"not"~"now", "are"~"age" similar) — hence the same-first-letter rule,
dropping "not"/"same" as stopwords, and removing "age" from D9. Second,
shared words ("many", "thing", "teach", "know") let runner-ups sit 1
point behind; weights were rebalanced so each canonical wins by ≥ 2
(e.g. "corrections" scores apart from "correct"; C19 needs 6). Dev
result at freeze: exp99 40/40, exp100-80 WRONG 0 (48/50 content
rephrasings CORRECT, 20/20 NEW decline).

## Freeze and blind run

Router hashed (sha256 in PASSMARKS.md), PASSMARKS sealed with shasum,
ledger P105.1–P105.5 appended — all before the panel was opened. The run
script aborts unless the router hash and the panel seal verify. One
0.9 s run: gate exact, K1 6/100 WRONG (FAIL), K2 43/70 (FAIL), K3 8/10
(FAIL), K4 PASS (40/40, exp100-80 zero WRONG). Zero invented
names/numbers: all 6 WRONGs are live-true neighboring-intent content —
formal synonyms ("individuals"), capability readings of forget-words,
and count questions about Tom or the future, which no guard covers.

## What next (not implemented)

Person/subject guard ("Tom knows" ≠ "I know"), tense guard ("will know"
≠ "know"), and a capability-vs-history split for forget/correct words
would address 5 of the 6 blind WRONGs; each is a second change, so each
needs its own experiment. The margin-2 decline path already converts
most ambiguity into honest declines (51/100 here), which is the behavior
to preserve while extending coverage.
