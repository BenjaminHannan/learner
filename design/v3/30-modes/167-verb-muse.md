# 167 — Verb-phrase facts map onto existing relations (Muse)

## The bug (file:line first)

- Loop162b clarifies every verb-phrase turn: "Kwame lives in Accra." ->
  "I didn't understand that. Could you say it another way?" The reply comes
  from the FakeEars.hear fallthrough (scripts/fable_agent_loop.py:148):
  no stage matches -- `_STATEMENT` needs "is", bench73 templates need their
  exact shapes ("was born in the city of", :114), the 162/162b frames need
  possessives. Meanwhile the possessive form of the same fact saves:
  "Kwame's city is Accra." -> teach (FakeEars `_STATEMENT` + `_chain`).
  "Kwame is married to Ama." is the one exception: bench73:96 owns it and
  teaches (Kwame, spouse, Ama) today.
- Ben's ruling (2026-09-22): anything that can be read as a relation
  should be.

## The inventory (read first; the table may only reuse these)

1. FakeEars possessive inventory (scripts/fable_agent_loop.py, FakeEars.hear):
   any "X's R is V" with a one-word X teaches (X, r, V) and "Who/What/Where
   is X's R?" answers it. Evidenced pre-seal on loop162b: city, employer,
   spouse, place_of_birth all save and answer. The demo pairs city with
   "lives in" already (scripts/fable_demo88_rehearse.py:60-61: "teach Ana
   city = Porto" / "Ana lives in Porto.").
2. ALLOWED_KEYS (scripts/fable_fix162_thename.py:73-79, 42 keys): contains
   employer, spouse, place_of_birth (B92 cues include 'works for' and
   'born'); does NOT contain city.
3. bench73 STATEMENT_PATTERNS (scripts/fable_bench73_english_arm.py:73-128):
   owns "X is married to Y" (-> spouse, :96) and "X was born in the city
   of Y" (-> place_of_birth, :114).

## The closed table (fixed here before any panel read; the only change)

| verb phrase | inventory relation (source) | statement twin | question twin | owner |
|---|---|---|---|---|
| lives in | city (FakeEars; demo88) | "X's city is Y." | "Where is X's city?" | 167 claims |
| works for | employer (ALLOWED + B92 cue) | "X's employer is Y." | "Who is X's employer?" | 167 claims |
| is married to | spouse (ALLOWED + bench73:96) | -- (base teaches today) | -- (future work: needs wife~=spouse) | base owns stmts; Q declined |
| was born in | place_of_birth (ALLOWED + B92 cue) | "X's place of birth is Y." | "Where is X's place of birth?" | 167 claims, except "the city of" shape (-> bench73:114) |

Mechanism (scripts/fable_fix167_verb.py, Verb167Mixin, stacked outermost as
Loop167Ears in scripts/fable_loop167_agent.py): a claimed turn is rewritten
to its twin string and handed to super().hear(). No save/ask/screen code of
its own -- value, hearsay, subject screens, _act guards, corrections, and
the mouth run as the possessive turn runs today, so each mapped statement
writes exactly the fact the possessive form writes, by construction.

Claimed shapes only (strict full-turn): single capital-lead token subject,
not closed-class (150c whole-subject veto); statements need trailing "."
or nothing, no "?" anywhere, no ";", optional Actually,/No, prefix
(preserved onto the twin); questions are the four wh-shapes with does/do.

## Never writes (safe decline to the base clarify path)

Negations (doesn't/does not/isn't/wasn't/never), tense changes (lived, used
to live, will live/move, worked, is working, was married), hedges (I think,
Maybe, Rumor has it, probably, might, Did ...?), hypotheticals (If ...,
Would ...), yes/no verb questions, multi-word subjects, the bench73-owned
shapes above. Hedges fail the subject shape (lowercase-led/multi-token), so
they never reach a twin.

## Limits (claims never exceed evidence)

- city is FakeEars-inventory only, not an ALLOWED_KEYS entry; The-name
  "lives in" and drummer/editor-class verbs stay out (future work, listed
  in RESULTS.md).
- Multi-word subjects ("Kwame Mensah lives in Accra.") fall through to the
  base clarify, exactly as today -- the twin would hit the one-word-names
  rule, so claiming it would only move the reply text.
- "Where was X born?" synthesises the Where-form possessive question; the
  sealed probe evidences it answers like the What-form.

## Reproduce

Sealed config + 61-case probe in artifacts/fable-verb167-20260922/;
scripts/fable_fix167_probe.py (twin-check vs base), scripts/fable_fix167_bench.py
(vs the base folder's frozen loop162b rows), scripts/fable_fix167_g3.py,
scripts/fable_marks123_all.py --agent scripts/fable_loop167_agent.py
--config .../loop167-config.json --workers 2, scripts/fable_fix167_marksdiff.py.
