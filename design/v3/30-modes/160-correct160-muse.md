# 160 — Bare corrections (exp 160, Muse)

## Step 1 — the code responsible (read before sealing)

A bare correction such as "no wait, it's Denver" is ignored because no
correction-prefix rule accepts it:

- `scripts/fable_agent_loop.py:95` (`_CORRECTION`: only `actually`/`no,`
  plus a full sentence). "no wait, it's Denver" matches no prefix, then
  `_STATEMENT` splits "no wait, it" into a 1-part chain and clarifies.
- `scripts/fable_loop102_agent.py:92` (`_CORRECTION_PREFIX_RE`, the rule
  the real chain actually uses via `Loop121Ears.hear` F3): accepts
  `actually,`/`actually `/`no,`/`correction:`/`sorry[ ,] I meant` plus a
  full sentence. "no wait, it's Denver" matches none, the bench73/extra
  teach-template parse of the whole turn returns None, and the exact old
  path clarifies with 0 writes. The taught triple stays stale (exp 152,
  class N6, S3 turn 6).

## The one change

`scripts/fable_fix160_barecorrect.py` (`BareCorrect160Mixin`), stacked in
`scripts/fable_loop160_agent.py` as loop160 = loop150 + mixin (ears hear
tag, loop `_act` resolve, `_listening_tick` previous-triple memory; loop150
imported read-only, nothing edited). A bare correction
("no wait, it's V" / "wait, it's V" / "sorry, it's V" / "I meant V" /
"no, V", sealed shapes in PASSMARKS.md) applied to the session's most-recent
saved teach (the latest user turn that stored exactly one teach/correct
triple; intervening questions, clarifies, refusals and small talk neither
set nor clear it, only a newer stored teach replaces it) synthesizes
`correct` with the same name/relation and value V through `super()._act` — the existing correction
machinery, so guards, the "Saved: ..." reply, audit trail and supersede
rules are identical to the "Actually, ..." form. With no saved teach yet
in the session it answers
`Which fact should I change? You can say e.g. "Actually, Tom's city is Denver."`
with 0 writes. Non-matching turns never re-tag, so they are byte-identical
to loop150. The previous triple persists in `state.json` (`last_teach160`).

Correction (2026-09-22, post-seal, re-sealed, see RESULTS.md deviations):
v1 said "IMMEDIATELY previous user turn" strictly (question/refusal/
small-talk/two+-turns-ago previous turn -> clarify). That clarifies on the
sealed N6 session turn itself (S3n6: teach 3 turns back, previous turn a
question), so it cannot meet the sealed C2 bar "the N6 turns become OK".
The memory is the most-recent saved teach, which is also what "right after
teaching" in the task title means for that session.

## Why this shape

- Session-local memory (not a global default) keeps the rule conservative:
  "no, Austin" can only rewrite what was just taught, never an old fact.
- Value validation (no `?`/`!`, no possessive, no copula, <= 8 words, no
  bare question words, no leading "to ") keeps questions ("wait, who is
  Tom's boss?"), full teaches ("wait, Tom's city is Denver.") and
  hedges ("I meant to ask ...") on the exact base path.
- Deliberate: a bare "no, thank you" right after a teach rewrites the
  value to "thank you" — the sealed "no, V" shape, no exception carved.

## Risks / non-goals

Pronouns ("it's" = which entity?) are not resolved — the previous triple
supplies the subject, which is the whole rule. Multi-turn staleness
("Actually" 2 turns later) still uses the explicit form. No sleep, reasoner
or mouth changes.

## Insertion points

- `hear()` tag: `fable_loop160_agent.py` `Loop160Ears` (outer ears).
- `correct` synthesis: `Loop160AgentLoop._act` via `super()._act`.
- Memory: `Loop160AgentLoop._listening_tick` fold + `_save`/`_load`.
- Adapter: none needed — triples, not embeddings, cross the boundary.
