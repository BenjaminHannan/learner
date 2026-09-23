# 167d — Widened verb-phrase table: works-at and speaks (Muse)

## The gap (file:line first)

- Loop167b clarifies four everyday turns the director probed 08:57 on
  2026-09-22: "Tom works at Acme.", "Where does Tom work?", "Rana
  speaks Hindi.", "What language does Rana speak?" -> "I didn't
  understand that. Could you say it another way?" (scripts/
  fable_agent_loop.py:148, the FakeEars fallthrough). The possessive
  form of each fact already saves and answers: "Tom's employer is
  Acme." -> teach (Tom, employer, Acme); "Rana's language is Hindi."
  -> teach (Rana, language, Hindi). Verified pre-seal on loop167b.
- Ben's ruling (2026-09-22): anything that can be read as a relation
  should be. Exp 167d is one change on loop167b
  (scripts/fable_loop167b_agent.py, scripts/fable_fix167b_valuescreen.py):
  widen the closed verb table by four rows only.

## The inventory (read first; the table may only reuse these)

1. FakeEars possessive inventory (scripts/fable_agent_loop.py,
   FakeEars.hear): any "X's R is V" teaches (X, r, V) and "Who/What/
   Where is X's R?" answers it. Evidenced pre-seal on loop167b:
   employer and language both save and answer.
2. ALLOWED_KEYS (scripts/fable_fix162_thename.py:73-79) contains
   employer; the twin rewrite bypasses the-name and lands on the
   FakeEars possessive path, so language needs no allow-list entry
   (same construction as 167's city).
3. bench73 owns two shapes the table must NOT take:
   scripts/fable_bench73_english_arm.py "X is married to Y" (-> spouse)
   and "X speaks the language of Y" (-> languages_spoken_written_or_
   signed; teaches redteam136 C033 today).

## The added table (fixed here before any registered run; the only change)

| verb phrase | inventory relation (source) | statement twin | question twin | owner |
|---|---|---|---|---|
| works at | employer (FakeEars; ALLOWED + B92-adjacent) | "X's employer is Y." | -- | 167d claims |
| speaks | language (FakeEars) | "X's language is Y." | -- | 167d claims |
| (Where does X work?) | employer | -- | "Who is X's employer?" | 167d claims |
| (What language(s) does X speak?) | language | -- | "What is X's language?" | 167d claims |
| "Who does X work for?" | employer | -- | "Who is X's employer?" | 167 owns; 167d never claims (disjoint shapes) |
| "X speaks the language of Y" | languages_spoken_written_or_signed (bench73) | -- (base teaches today) | -- | base owns; 167d declines (veto, same precedent as 167's "the city of") |

Mechanism (scripts/fable_fix167d_verb.py, Verb167dMixin, stacked INSIDE
the untouched 167b screen as Loop167dEars in
scripts/fable_loop167d_agent.py): a claimed turn is rewritten to its
twin string and handed to super().hear(). No save/ask/screen code of
its own -- value screening reuses S167B.screen_value (loop139e tail
strip + determiner/lowercase veto; S167B's twin regex only matches
167's three surfaces, hence the rebuild here), subject veto reuses
150c, corrections and the mouth run as the possessive turn runs today.

Claimed shapes only (strict full-turn): single capital-lead token
subject, not closed-class (150c whole-subject veto); statements need
trailing "." or nothing, no "?" anywhere, no ";", optional Actually,/No,
prefix (preserved onto the twin); questions are the two wh-shapes with
does/do, singular or plural "language(s)".

## Never writes (safe decline to the base clarify path)

Negations (doesn't/does not work/speak), tense changes (used to work,
worked), hedges (maybe, I think), hypotheticals, yes/no verb questions
("Does Rana speak Hindi?"), reverse questions ("Who works at Acme?"),
description objects ("a big firm near Oslo", "a dialect" -- determiner
veto; "hindi" -- lowercase veto), multi-word subjects, tail-only
objects, and the two base-owned shapes above ("Who does X work for?"
stays V167's; "speaks the language of" stays bench73's).

## Limits (claims never exceed evidence)

- language is FakeEars-inventory only, like 167's city; drummer/class
  verbs and further relations stay out (future work, in RESULTS.md).
- Multi-word subjects fall through to the base clarify, exactly as
  today -- the twin would hit the one-word-names rule, so claiming it
  would only move the reply text.
- "Where does X work?" synthesises the Who-form possessive question
  (the twin 167 already uses for "Who does X work for?"); "What
  languages ...?" (plural) synthesises the singular possessive
  question; the sealed probe evidences both answer like the twin.

## Reproduce

Sealed config + 32-case probe in artifacts/fable-verb167d-20260922/;
scripts/fable_fix167d_probe.py (T1 twin-check vs base loop167b + T2
167b-probe identity), scripts/fable_fix167d_bench.py (vs frozen
loop167b/loop162b rows), scripts/fable_fix167d_g3.py,
scripts/fable_marks123_all.py --agent scripts/fable_loop167d_agent.py
--config .../loop167d-config.json --workers 2,
scripts/fable_fix167d_marksdiff.py.
