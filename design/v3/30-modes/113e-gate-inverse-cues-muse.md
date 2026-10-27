# 113e — The gate learns the reverse direction (Muse, 2026-09-22)

For Ben in plain language: last time (exp 113d) the assistant learned to
stay quiet when it only half-understood a question — but the rule only knew
words in one direction. Asked "Who is the author of Oaken Melodies?", the
assistant correctly worked out (author_of) but the rule didn't recognise
"author" as the same relation, so it stayed quiet on 15 questions it
actually knew, plus a few family-word ones ("mother's husband",
"birth year"). This experiment teaches the rule the reverse direction:
for each relation, it now also accepts every wording the assistant's own
code tables already use for that relation or its inverse. Nothing is
hand-added and no benchmark wording is copied — the words come mechanically
from tables already in the repo, and the full added-word list is printed
into the artifact.

## The one change

`scripts/fable_loop113e_agent.py` (new, prefix-owned; nothing else edited).
`build_cue_sets()` unions, per relation node: `REL_CUES92` cues (B73 mention
cues + B92 extras); every `LE.RELATION_MAP` surface whose canonical value
is the node (`mom`/`mum` -> mother, `work`/`works for` -> employer,
`made`/`created` -> creator); every `CLOSED_MAP` webred surface for the
node (`place of birth`, `educated at`, `mother` ...; asserted equal to the
`relations.json` closed map that feeds the ears `CLASSES` table); the
parser's own reversal declarations (`REV_OF_NOUNS`: `author` -> author_of
..., `REV_BY_VERBS`: `written` -> written_by ..., with each verb also
joined to the relation whose cues contain it); and the frozen wikidata
inverse edges that hit our vocabulary (creator <-> notable_work, capital
<-> capital_of, officeholder <-> position_held, manufacturer <->
product_or_material_produced, spouse <-> spouse). Each node also deletes
its own snake/space spellings (the parser's `FakeEars._relation` rule), so
a walked relation with no table entry (`birth_year`, `pet`) at least
consumes its own mention. Union-find components give R + inverse(R) the
same cue set. `frame_consumes_question_113e()` is 113c's gate verbatim
except it deletes/leftover-scans with these sets (same qualifier rule,
same longest-first substring deletion, same entity-span deletion, same
word-boundary test, same `_DROP_CUES`).

`Loop113eEars` subclasses 113d's ears with the same routing (composer
branches + guarded loop102 fallback), calling the new gate; teach path and
non-ask actions inherit byte-identical. Runners reuse 113d's scripts by
import with class swap (`fable_bench113e_*`, `fable_loop113e_marks.py`).

## Pre-seal expectations (ledger P113e.1-5)

Reversals should repair (15 Edit items consume again); toy-family items
whose words the tables know (`mother`/`husband`/`job`/`pet`/`birth year`)
should repair; P4-24 (`birth year` own spelling) should repair. Deliberately
NOT repaired by this change: Edit-200 088 (`position` is a different
relation's cue, not an inverse surface), 096 (`origin` likewise), trailing
qualifiers (`in 2019`), toy words no table knows. Forecast: E2 198/200,
L5-Z1 58/60 — i.e. a registered FAIL on E2/E4 with the repair demonstrated,
provided no genuine prefix un-abstains (the risk is watched per-item in E1
and E3: 056/103/196, the 7 fixed bench121 cases, B5/B3/Q2/U1/V4).

## Limits

Question-side routing only. The gate still cannot see qualifier semantics
or descriptive/synonym phrasing; relations unknown to every table still
consume only their own spelling. Fable-Edit/L5/P4 items were seen by 113d,
so this measures repair, not generalisation.

## What it means

A consumption gate must speak every direction its own parser speaks: giving
each relation the surfaces of its inverse (from the repo's own tables)
restores legitimate answers without touching genuine-prefix protection.

## What it does not mean

It does not mean the assistant knows more or generalises better: restored
answers are ones the fallback already produced under 113c; anything still
outside the tables' vocabulary stays quiet.
