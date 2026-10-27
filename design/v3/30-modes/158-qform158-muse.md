# 158 — Question-surface normalisation (qform158, Muse)

Exp 152 (phone sessions, both targets byte-identical) found two
question-shape classes that refuse although the fact is taught:

- N5: `what's tess's city?` / `tell me tess's city` -> clarify, fact known.
- N7: `Who is Rosa's mother's city???` -> `I don't know Vera's city??.`

## Responsible code (read-only, never edited)

- `scripts/fable_agent_loop.py:94` — `_QUESTION =
  ^\s*(?:who|what|where)\s+(?:is|are)\s+(.+?)\s*[?.]?\s*$`. Accepts only
  `who|what|where + is|are` (N5: no `what's`, no imperatives), and the
  trailing `[?.]?` strips exactly ONE mark (N7: `city???` leaves `??`
  inside the relation, answered as `Vera's city??`).
- `scripts/fable_loop121_agent.py:175` — question-vs-statement routing:
  a turn ending in `?` takes the question side (exact loop113b); anything
  else takes the teach path. `tell me tess's city` (no `?`) never reaches
  any question parser.
- `scripts/fable_loop113b_agent.py:70` — `?` turns run the N-hop router
  with fallback to the loop102 chain (which ends at the `FakeEars`
  parser above); non-`?` turns delegate to the loop102 chain.

Exp 151 (running separately) owns bare `What is X's R` with NO `?`; this
experiment never touches that case.

## The one change

`scripts/fable_fix158_qform.py` (`normalize_question_surface` pure
function + stackable `Qform158Mixin`), layered at the outermost ears
`hear()` in `scripts/fable_loop158_agent.py` (`Loop158Ears` over
loop150 ears; loop150 = loop129b + 139b value guard + 150 subject guard,
imported read-only). Normalisation, applied in order:

1. `tell me|show me|give me X's R` -> `What is X's R?` (only when the
   remainder already starts with a question word/auxiliary, kept as-is,
   or contains a possessive `'s`); `tell me who/what ...` -> the bare
   question. Non-possessive remainders (`tell me more`, `show me the
   money`) do not fire.
2. Leading `what's|who's|where's|when's` (straight or curly apostrophe)
   -> `what|who|where|when is`. Leading position only.
3. Trailing `[?.!]+` collapsed to one `?`.

The rewrite is RETURNED only when all hold: the candidate differs, the
original contains `?`/`!` OR rule 1 fired (so bare statements, bare
`.`-teaches and 151's no-`?` territory are never eligible), and the
candidate fed through the UNCHANGED loop yields an `ask` action.
Otherwise the original turn goes through untouched, so any rewrite can
only convert a clarify-miss into the canonical-question reply, never
alter a teach, a clarify, or an already-answering question. Question
actions never write, so 0 new writes by construction.

## Why this is safe for the regressions

Bench questions are canonical single-`?` `Who/What is ...?` forms: no
rule fires, candidate == original, byte-identical path. Suite inputs
were scanned pre-seal for leading contractions, tell/show/give-me
openers and `?`/`!` stacks landing on an ask-shaped candidate (see
PASSMARKS.md). The only 152 turns that change are S5 n5/n6/n9, which
become their canonical answers.

## Files (all new, prefix `fable_fix158_` / `fable_loop158_`)

`scripts/fable_fix158_qform.py`, `scripts/fable_loop158_agent.py`,
`scripts/fable_fix158_probe.py` (Q1), `scripts/fable_fix158_bench.py`
(G1, imports `fable_loop129b_bench` runners), `scripts/fable_fix158_session.py`
(G3, imports `fable_session152_run`), config
`artifacts/fable-qform158-20260922/loop158-config.json`, probe cases
`artifacts/fable-qform158-20260922/cases158.json`.

What it means: phone question shapes (`what's`, `tell me`, `???`) get
the same answer as the canonical form.
What it does not mean: pronouns, small talk, `mom`, bare corrections
and the N9 wrong-answer class are untouched (other experiments' scope).
