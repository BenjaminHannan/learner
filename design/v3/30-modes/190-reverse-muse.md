# 190 — reverse questions by VALUE lookup (design)

loop190 = loop138g + ONE change. New files only:
`scripts/fable_fix190_reverse.py` (the rule),
`scripts/fable_loop190_agent.py` (the stack),
`scripts/fable_fix190_{v1,suites,marks,bench}.py` (drivers). No existing
file edited or committed.

## Problem

Director probe on loop138g: `Who was born in Paris?` and similar
reverse questions get the generic don't-know; the notebook is keyed by
(subject, relation) and nothing looks it up by VALUE. The 153 stage
already in the stack answers only four frames on a forward MISS, so
`Who has Lee as their boss?`, `Who lives in Oslo?`, `Who was born in
Paris?` all miss, and the whose-shapes it does answer get `V is the R
of S.` wording instead of the forward `S's R is V.` sentence.

## The change

`Reverse190Mixin.hear()` runs the full 138g stack first and only acts
when it returns all-clarify, so forward asks and teaches are
byte-identical by construction. On a closed shape it scans
`L90.notebook_triples` (live taught facts: corrections respected,
inferences never) for the relation key with the matching current value
and returns one clarify (never writes; the clarify carries no `didn't
understand`, so the 168 grounded-self gate serves it verbatim).

Closed shapes: E1 `Whose <R> is <Y>?`; E2 `Who has <Y> as their|his|her
<R>?` (`its` stays with the sealed 153 frame); E3 `Who lives in <Y>?`
→ city key (loop138g stores city; its wh-city port answers town shapes
via the city path); E4 `Who was born in <Y>?` → birthplace key. R/Y are
single noun phrases (153's cue list); E1/E2 need R in the closed set.

Closed relations (union of relations loop138g's own code names):
PERSON_RELATIONS (`fable_agent_loop.py:91`) + LISTED_RELATIONS
(`fable_fix139e_tail.py:57`): mother, father, sister, brother, sibling,
spouse, husband, wife, boss, friend, teacher, coach, pet, dog,
neighbour, neighbor, partner, city, town, hometown, home_town, country,
birthplace, place_of_birth, school.

Replies: 1 match → `Kim's boss is Lee.`; several → one sentence each in
notebook order; none + known Y → `I don't know anyone whose R is Y.`;
unknown Y → `I don't know anyone called Y.` (notebook UNKNOWN_ENTITY
text). Known = alias, live subject, or live value (case-insensitive).

## Composition

`Loop190Ears(Reverse190Mixin, Loop138gEars)`: the 190 stage is
outermost. No `_act`/`turn()` override; 153 keeps its three other
frames (`Who is Y the R of?`, `Y is the R of whom?`, `its`-frame) and
all unlisted-relation replies byte-identical. Reasoner, notebook,
sleep145, settle daemon unchanged.

## Known edges

- 153 whose-replies are overridden with forward-style sentences; 153's
  blanket no-match splits into known vs unknown-name (intended moves).
- `Who lives in …` overrides a smalltalk grounded reply; `Who has … as
  their …` / `Who was born in …` override the decline (intended).
- Value match is case-sensitive (153 semantics); compound/multi-hop
  shapes keep the base clarify (out of scope, never answered wrong).
- Pre-seal static scan: no frozen-suite, marks123, bench or soak turn
  matches the closed shapes, so V2/V3 predict zero moves.

## What it means / what it does not mean

It means reverse questions over already-stored relations are answered
from the notebook by value. It does not mean new relations are learned,
inferences are stored, or any ask path writes.
