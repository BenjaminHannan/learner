# 100 — Self-questions under blind phrasing (Muse, 2026-09-22)

Exp 99 showed the model answering 40 scripted questions about itself (40/40
from live state). Its answerer parsed those exact templates, so the demo
risk was obvious: Ben's uncle phrases things his own way. Exp 100 is the
blind test: 80 new questions written from the intent list alone, sealed
before the answerer was ever opened, then asked against the identical live
session. Result: registered FAIL — 27/60 rephrasings correct, 5 confident
misfires, 0 invented names/numbers.

## Blind method (why the numbers can be trusted)

Step 1 used only the exp-99 transcript and intent ids. The 60 rephrasings
(2 each for C1–C20, 1 each for C21–C30 and D1–D10) use casual speech,
long-winded forms, typos ("hw many"), contractions, and "so, um, …" openers;
20 further questions use genuinely new intents (oldest thing known, least
sure fact, how belief is decided, what happens on correct/forget, gaps).
`PASSMARKS.md` + `QUESTIONS.md` were hashed before `fable_self99.py` was
opened; predictions P100.1–P100.4 were ledgered first. Step 2 imported the
answerer read-only, rebuilt its exact session (gate: 19 taught, 6 people,
1 quarantine, 2 corrections, 1 forgotten, 0 sleeps, 26 turns — exact), asked
via `answer_self()` with no new turns, and scored by script: CORRECT iff the
answer passes exp 99's own per-intent value check; WRONG iff it hallucinates
a name/number or passes a *different* intent's check; otherwise DECLINE iff
it carries a decline marker or is the exact content-free fallback.

## What broke (taxonomy from the 5 WRONGs + 19 misses)

Exact-substring routing is the whole story. Inflection: "taught" does not
contain "teach" (Q05 last-taught missed); "told"/"tell" miss "taught" (Q06,
Q09 provenance missed). Typos: "hw many" misses "how many" twice, turning
two count questions into list answers (Q23, Q24 WRONG). Synonyms: "folks"
(Q04), "things" (Q02), "certain" (Q30), "right before" (Q34) all fall back.
Contractions: "don't" misses "do not" (Q43). Exact equality: C24 requires
the whole string to equal "what can you do?", so ", anyway?" falls back
(Q44). Branch order: "internet" is tested before "believe", so a belief
question starting with "internet" gets the holdings answer with a
misleading leading "Yes" (Q14 WRONG — the only safety-adjacent misfire).
Count-vs-list: "count …" and "how many times …" hit the list branches
(Q24, Q28 WRONG). New intents mostly decline honestly (19/20); the one
misfire (Q69) shows any correction vocabulary triggers the correction-list
branch regardless of the process asked.

## The good news, precisely stated

Nothing was invented: all 80 answers passed the live-state name/number
scan, all 10 decline rephrasings declined properly, and 38 unparsed
questions got an honest "I do not understand" rather than a guess. The
failure is coverage and routing precision, not honesty — except Q14's
leading "Yes", which is a real (small) honesty blemish: a yes/no belief
question answered "Yes…" by the wrong branch.

## Fix sketch (not implemented — brief forbids touching fable_self99.py)

Normalize before routing (stem taught→teach, fix hw→how, expand
contractions), use substring triggers instead of exact equality, add a
count-vs-list guard (forms like "how many/count/times" force count
branches), and order "believe" above "internet". Expected effect from this
run's evidence: ~19 fallbacks recovered, all 5 WRONGs removed — but that
claim is a prediction, not a result; it needs its own sealed rerun against
fresh phrasing (a v2 must not reuse these 80 questions as training).

## What it means

A template router cannot carry the family demo: natural phrasing halves its
coverage and occasionally aims it at the wrong true fact.

## What it does not mean

The notebook, loop, and values are exonerated — every stated fact was true.
This says nothing about a real English front end, only about scaffolding.
