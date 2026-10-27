# 137c — hypothetical openers never write (design)

Exp 137's upgrade accepts any 2–4 Title-case tokens as one possessive
subject (`scripts/fable_fix137_names.py:123-127`, called from
`scripts/fable_loop138b_agent.py:142-169`). Loop137b strips discourse
openers and re-teaches the rest (`scripts/fable_loop137b_agent.py:125`,
`rest = D137B.strip_first_token(...)` inside `_upgrade137b`, lines
109–131; phone-fronted "?" strip lines 163–178). So on loop137b
"Suppose Kim's boss is Lee." re-parses as "Kim's boss is Lee." and SAVES
it (director probe 05:16; sealed redteam136 C089 stores
`[Tom,boss,Ann]`, verdict WRONG-WRITE). "Imagine Kim's boss is Lee."
saves too. "What if Kim's boss is Lee?" and "If Kim's boss is Lee then
Lee is busy." are already declined safely on loop137b.

## The one change

`Loop137cEars` subclasses loop137b's ears
(`scripts/fable_loop137c_agent.py`, new files only, no loop137b file
edited) and checks `is_hypothetical(turn)` FIRST — before any panel
read, before the unchanged loop137b pipeline runs. A turn whose first
words (after optional case-insensitive fillers ok/so/and plus
punctuation) are a closed-list marker — suppose, supposing, imagine,
pretend, pretend that, let's say, lets say, hypothetically, in theory,
what if, say that (fixed before any panel read, in
`scripts/fable_fix137c_hypo.py`) — never reaches any teach path: it
returns one clarify carrying the exact sealed reply
"OK, I'll treat that as pretend, so I won't save it.", rendered
verbatim by the normal `_act`/mouth path with zero writes and zero
self-routing (the text holds no "didn't understand"). Later questions
in the same session therefore answer only from real saved facts —
there is nothing else to read, because the pretend turn stored
nothing. Everything else falls through to `super().hear()`
byte-identical.

## Deliberate scope edges

- "say" ALONE is not a marker (only "say that" is): 137b's "Say Tom's
  ..." teach stays identical. Bare "if" is not a marker (only "what
  if"): "If Kim's boss is Lee then ..." stays declined exactly as on
  137b. "Okay" is not a filler (only ok/so/and).
- A marker glued to a possessive 's is a name, not a hypothetical:
  "What If's boss is Kim." teaches `[What If,boss,Kim]` exactly as on
  137b (verified live pre-seal). Marker words later in the sentence
  ("Kim's song is Imagine", "Kim's film is What If") never match: only
  turn-initial position counts.
- "What if ...?" moves from the base decline to the pretend reply by
  design (never writes either way). "Btw./So/Hi." phone teaches that
  137b now saves stay byte-identical (not markers, not fillers+markers).
- Boundary rule: the marker needs end/whitespace/punctuation after it,
  so "Supposedly ..." and "Imagines ..." never match. Case-insensitive
  throughout ("SUPPOSE Kim's ...").

## What it means / does not mean

It means hypothetical-led turns never write and always say the exact
pretend sentence, while every other turn is bit-identical to loop137b.
It does not mean hypotheticals are understood (no counterfactual
reasoning; the content is simply refused), nor that titles in 137
position survive (137b's "Hey Jude" edge is inherited unchanged).
