# 222 — "IS A R OF" ONLY FOR ONE-OF-MANY PERSON RELATIONS (Muse)

## Problem

Exp 215 taught the loop to read "X is the R of Y." as "Y's R is X." for
any relation word R. The definite form is almost always right ("Oslo is
the capital of Norway."). The indefinite form is right only for
one-of-many relations ("Nell is a friend of Otto." — Otto can have many
friends). For other nouns it invents junk: "Kip Dune is a citizen of
Peru." saved `(Peru, citizen, Kip Dune)` (breaking the 138i triple and
its question), and "Lima is a city of Peru." saved `(Peru, city, Lima)`,
so "Where does Peru live?" answered "Peru's city is Lima." — "city" is
the where-someone-lives relation, and Lima is not someone.

## Design

Gate, don't re-parse. Loop222 subclasses `Loop215Ears` and overrides
only `hear`: for non-questions, it asks 215's own `rewrite_teach215`
whether 215 would rewrite. If yes, and the article is a/an, and the R
surface is not in the allow-set, it calls `Loop138iEars.hear` directly —
the exact 138i path, with the 215 mixin skipped. Everything else
("The" teaches, all questions, allowed indefinite R) runs the exact 215
path, so behavior there is identical by construction, not by
re-implementation.

The allow-set comes from the frozen relation table (read-only at
import): entries with `value_kind == "person"` and
`cardinality == "multi"`, canonical names plus aliases, lowercased
(34 names; e.g. friend, daughter, apprentice, grandma→grandmother,
kid→child, coworker→colleague). Why this set: one-of-many is exactly
when "Y's R is X" adds a fact without claiming R names Y's single
something; single-valued person relations ("a mother/boss of") and
non-person nouns ("a city/citizen of") stay on the base path, which
already handles the true readings (e.g. citizen→country_of_citizenship).

No new storage keys, no question-side change, no sleep/reasoner/mouth
change. Two new files; loop215 and loop138i untouched.

## Evidence

B1: C013 + Lima byte-identical to 138i (replies and triples); friend,
daughter, capital, sister scenarios byte-identical to 215. B2 (40 fresh
fictional cases): 20/20 person/multi identical to 215 with (Y,R,X)
storage; 20/20 other nouns identical to 138i; 0 junk writes. B3: moved
set = 215's minus C013 case-by-case (rt136 C019–C031, rt143 J8/K9/O3,
bench f00–f24-fwd, sessions 0), every moved row byte-identical to 215's
sealed rows; hand-checked verdicts (J8 abstains on a typo instead of
repeating the base's wrong answer). B4: sleep smoke identical to 138i
(installed, 5/5 probes, 0 wrong, 0 overwrites). B5: 0 new wrong writes.

## Limits

The gate is only as good as the table: a person+multi relation missing
from the table (or a new alias) falls back to 138i behavior (a refuse),
never to junk — fail-safe direction. Stale golds that reward junk
echoes (13 rt136 triples, 25 bench rows) still score the fix as wrong;
that is a gold problem, flagged for Ben, not a behavior problem.
