# 223 — Negated capability questions pass the question screen (Muse)

## Problem
On loop138i, "What can you do?" is served the fixed CAN sheet, but "What
can't you do?" is stopped by the exp-148 question screen (sealed triggers:
not, never, n't, no one, nobody, none, years, "as of", before, after,
formerly, originally, "used to", currently) and gets the negation clarify.
The self router (frozen route127, scripts/fable_self127.py) already routes
such turns to C25 and the fixed CANNOT sheet exists (CAPABILITY_CANNOT in
scripts/fable_self99.py) — the screen just runs first and never asks.

## The one change
`scripts/fable_loop223_agent.py` subclasses loop138i (no earlier file
edited). `Loop223Ears.hear` mirrors the screen's own detection gate
(trailing "?", notebook-triples exemption, `S148.trigger_spans`) to decide
whether the screen would stop the turn. If it would, it consults the
base's own router — `fable_loop138_agent._route127`, the exact call the
base makes on the notebook-miss path (MRO trace: `Loop138iAgentLoop` →
`Loop138hAgentLoop` → `Loop138gAgentLoop.turn` / `Loop138dAgentLoop.turn`
both call `L138._route127`). If the intent is C24 or C25 AND the turn has
a second-person word (you/your/yours/yourself), the `super().hear()` call
runs with `S148.trigger_spans` temporarily returning no hits
(process-local, try/finally), i.e. exactly the base path with the screen
absent: no `screen148b` tags, so `_act`, reasoner, mouth, and the `turn()`
self path run untouched. All other turns call `super().hear()` verbatim.

## Why this shape
- No router widening: three A-cases ("What don't you do?", "What will you
  never do?", "What are things you will never do?") route DECLINE; they
  are kept, marked "not capability", and expected byte-identical.
- No new reply text: capability replies are the base's own grounded
  C24/C25 sheets; everything else is base-identical by construction.
- Second-person gate: bare negations about third parties ("What can't Kim
  do?") stay screened; all 32 B-cases route DECLINE/D7 and stay screened.
- Fail-safe: any exception in detection/routing keeps the screen.

## Evidence (registered; sealed PASSMARKS.md)
76 probe cases (22 A / 32 B / 22 C, fresh loop pair per case, 4 shared
fictional teaches): M1 22/22 (19 exact C25 sheets + 3 byte-identical),
0 writes; M2 54/54 byte-identical reply + stored facts; suitediff vs 138i
0 moves on rt136, rt143, sessions152, bench; sleepsmoke206 identical to
138i (1 sleep, installed, 5/5 probes, 0 wrong, broken abstains, 50/50
taught, 0 overwrites); 0 new wrong writes anywhere. Verdict: PASS.

## Limits
Only C24/C25 + second-person "?" turns change; every other screened turn
(incl. "What do you do when you do not know something?", C23) still
screens. Counter side effect: a bypassed turn takes the self path instead
of the screen path, so per-turn counters can differ from the base after a
bypass — comparisons are per-case fresh, matching suite methodology.

What it means: negated "you" capability questions now get the CANNOT
sheet instead of the negation clarify.
What it does not mean: no other screening, routing, or reply text
changed; the router still declines what it declined before.
