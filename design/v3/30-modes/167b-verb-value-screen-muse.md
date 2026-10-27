# 167b — Verb-object value screen (Muse)

## The bug (file:line first)

- Loop167 saves whatever object the verb turn carries: "Ivy lives in a
  flat." -> (Ivy, city, a flat); "Uma lives in Accra now." -> (Uma,
  city, Accra now) (scripts/fable_fix167_verb.py:156-166 -- the twin is
  built from the raw value span with no value screen; the mixin owns no
  screens by design). The possessive path has the same gap, but Ben's
  ruling for THIS change covers the verb path only: one change at a time.
- Ben's ruling (2026-09-22): the verb path's object must be name-shaped
  before its possessive twin is handed on.

## The closed lists (fixed here before any panel read; the only change)

1. Tail strip: loop139e's sealed machinery
   (scripts/fable_fix139e_tail.py, sealed in
   artifacts/fable-tail139e-20260922/ with SEAL.sha256.txt; the strip is
   loop139c's strip_chat_tail, scripts/fable_fix139c_tail.py:46, which
   139e applies first and seals): SINGLES too, also, actually, though,
   tho, lol, lmao, haha, btw, again, now, anyway, then, instead, rn,
   right, ok, okay + PAIRS "as well", "i guess"; lowercase-only,
   trailing punctuation tolerated, repeats for stacked tails ("Pavel too
   lol" -> "Pavel"), at least one value word must remain (a value that
   IS just "now" refuses instead of storing empty).
2. DETERMINERS (scripts/fable_fix167b_valuescreen.py): a, an, the, my,
   your, his, her, its, our, their, this, that, these, those, some, any,
   no, every, each, either, neither -- matched case-insensitively
   against the stripped object's first word ("A flat", "The city"
   refuse; "The Hague" would refuse too -- conservative, disclosed).
3. Lowercase-first rule: a stripped object whose first character is
   lowercase (home, town, abroad) refuses. Multi-word names with
   capitalised words pass ("New York", "San Francisco"); lowercase
   connectors inside pass because only the FIRST word is tested
   ("Rio de Janeiro" would save).

Mechanism (scripts/fable_fix167b_valuescreen.py, ValueScreen167bMixin,
stacked outermost as Loop167bEars in
scripts/fable_loop167b_agent.py): 167's claim logic is reused verbatim
(V167.parse_verb_turn, read-only). Verb questions pass to the 167 path
literally. A claimed statement's twin is re-parsed, its object stripped
and name-checked; refused turns return exactly loop167's own clarify
("I didn't understand that. Could you say it another way?",
scripts/fable_agent_loop.py:148) with no write; passing turns hand on
the twin rebuilt with the stripped object, so writes/answers stay the
possessive path's own by 167's construction.

## Never writes (screen refusals + everything 167 declines)

Tail-only objects ("Kim lives in now."), article/determiner-led
objects ("a flat", "the city", "my house", "A flat", "The city",
"his uncle", "her hometown", "some town"), lowercase-led objects
("home", "town", "abroad"), plus every 167 decline (negations, tense
changes, hedges, hypotheticals, yes/no verb questions, multi-word or
closed-class subjects, two-sentence turns, married statements/
questions, born city-of shapes). Capitalised tails ("Accra Now") are
NOT stripped (139c is lowercase-only) and save as-is -- same as the
possessive path today.

## Saved-label ruling (not a second change)

"Raj was born in Pune." still replies "Saved: Raj's place_of_birth is
Pune." while asks answer "Raj's place of birth is Pune.". The two
renders are different functions -- FakeMouth.say's inline
`part.replace("_", " ")` (scripts/fable_agent_loop.py:166-167) vs the
notebook contract's TEMPLATES (scripts/fable_notebook_contract.py:77)
-- so the label is left as is. Future work: one shared relation-render
function for both paths (touches the notebook contract, out of scope
for a one-change verb experiment).

## Limits (claims never exceed evidence)

- The screen only narrows 167's claims; it never invents a write 167
  would not make. Any input 167 declines behaves byte-identical.
- Description refusal is shape-based, not meaning-based: a real
  nickname like "a flat" as a city name would refuse (conservative).
- The possessive path ("Ivy's city is a flat.") still saves -- this
  experiment covers the verb path only, per the brief.

## Reproduce

Sealed config + 64-case probe in artifacts/fable-verb167b-20260922/;
scripts/fable_fix167b_probe.py (exact-reply + twin-check vs loop167),
scripts/fable_fix167b_bench.py (vs frozen loop167 AND loop162b rows),
scripts/fable_fix167b_g3.py, scripts/fable_marks123_all.py --agent
scripts/fable_loop167b_agent.py --config .../loop167b-config.json
--workers 2, scripts/fable_fix167b_marksdiff.py (vs marks167, zero
moves predicted).
