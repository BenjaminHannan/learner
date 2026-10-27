# 190b — reverse no-match rewording (design)

loop190b = loop190 + ONE reply-text change. New files only:
`scripts/fable_loop190b_agent.py` (the wrapper),
`scripts/fable_fix190b_{v1,suites,marks}.py` (drivers),
`artifacts/fable-reverse190b-20260922/` (config, cases, rows),
this doc. No 190 file edited or committed.

## Problem

Director probe on loop190: a REVERSE-shaped question about a value
nobody has gets the who-is wording — `Who lives in Lima?` →
`I don't know anyone called Lima.` Lima is a city, not a person. The
190 split (known value → whose-sentence; unknown value → called) leaks
the notebook's unknown-person wording into reverse questions over
non-person relations.

## The change

`Reverse190bMixin.hear()` runs the full 190 stack first and only acts
when it returns a single clarify reading exactly
`I don't know anyone called <V>.` AND the turn parses as one of 190's
closed shapes E1–E4 (`parse_reverse190`) with the called name equal to
the parsed value. It then returns one clarify reading
`I don't know anyone whose <R> is <V>.` with the relation display name
(`_` → space, e.g. `home town`). Clarify-only, never writes; the
clarify carries no `didn't understand`, so the 168 grounded-self gate
serves it verbatim, exactly as 190's clarifies.

Untouched by construction: matches (190 answers stand), known-value
no-match (already whose-sentences), the three 153 frames 190 keeps
(`Who is V the R of?`, `V is the R of whom?`, `its`-frame — already
whose-form on no-match), forward asks, teaches/corrects, unlisted
relations, compound/multi-hop shapes. A plain who-is question about an
unknown name (`Who is Lima's boss?` → called; `Who is Lima?` →
decline) never parses as reverse and keeps its reply.

## Why a wrapper, not an edit

The brief demands the 190 agent file stay sealed. The wrapper matches
on 190's exact called-sentence plus the sealed parser, so it can only
fire where 190 itself produced the who-is wording for a reverse
shape — a strict, text-only subset. Notebook events are identical to
190 on every suite because no new action type, write path, or lookup
is introduced.

## Correction edge

After a correction removes the only match, the old value reads as
unknown on 190 (it says called), so 190b's move shows there too
(R13–R14). Genuine moves happen only for values with no live match —
the R1 case covers never-taught values (R1–R12) plus the
corrected-away value (R13–R14).

## Composition

`Loop190bEars(Reverse190bMixin, Loop190Ears)`: the 190b stage is
outermost. No `_act`/`turn()` override. Reasoner, notebook, sleep145,
settle daemon unchanged.

## What it means / what it does not mean

It means reverse questions with no stored match always name the
relation, never mislabel the value as a person. It does not mean new
relations are learned, inferences are stored, who-is wording changes,
or any ask path writes.
