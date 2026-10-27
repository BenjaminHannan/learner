# 158b — relation-word question rewriter on loop138b (design)

One new file (`scripts/fable_loop158b_agent.py`) subclasses the frozen
loop138b agent. `Loop158bEars(Loop138bEars)` adds THE ONE CHANGE: a
question rewriter stage before the fallback. `turn()` is inherited
verbatim (L2 self layer untouched); `_act`, mouth, reasoner, sleeper,
daemon settle rule and atomic-write clients are exactly loop138b's.

## How it works

`hear()` runs the full loop138b stack first (`super().hear`, which
already includes the 132 rewriter). If the base understood the turn
(anything but all-clarify), the result passes through untouched. Only
on an all-clarify do we try `rewrite_whrel(question, triples)`, then
run the rewrite through the base unchanged (`super().hear(newq)`) and
keep it only if it yields an ask; any teach/correct/forget2 in the
second pass is discarded, so questions never write.

`rewrite_whrel` is a pure function of (question, triples):

- Relation vocabulary: the loop's own relation tables, i.e. the
  notebook triple relation set (`notebook_triples`,
  `fable_loop90_agent.py:101`), matched with the same normalisation the
  base uses (`FakeEars._relation`, `fable_agent_loop.py:151-152`). The
  only static table is `PERSON_RELATIONS`
  (`fable_agent_loop.py:91-92`), which we only read about, never change.
- Entity gate: the first chain segment must match a taught
  subject/object (case-insensitive); every further hop must match a
  taught (subject, relation) pair (last-wins). Unknown X, unknown
  relation, or a broken chain passes through unchanged, so look-alikes
  ("What color is the sky?", "What time is it?", "How old are you?")
  behave exactly as the base.
- Shapes (a)–(c) map onto "What is <X>'s <R>?". Shape (d) uses a fixed
  table written before any panel read: When→birthday/anniversary,
  How-old→age, Where-from→hometown then birthplace, Where-live→city
  then home. For the Where shapes the candidate is picked per-X (first
  candidate taught for X's resolved entity) falling back to the first
  table candidate in the global tables, so the served relation always
  exists in the tables.

## Ordering and vetoes

The stage sits after everything in loop138b (148b screen, 132 rewrite)
and before the fallback (`fable_agent_loop.py:148,350`,
`fable_loop138_agent.py:81-93`), which it never edits. Canonical
possessives ("What is Rex's color?") never reach it. A rewritten
negation/time question re-enters the base and is screened there, never
answered around.

## Known edges (measured on loop138b, not guessed)

2-hop chains through non-person relations abstain in the base reasoner
("Tom's dog is Rex, which is not someone I can look up"), so "What
color is Tom's dog?" rewrites to a canonical form the base itself
abstains on — a rewriter cannot fix a reasoner limit. (b)-shaped 2-hop
is pre-parsed by the base into a wrong ask on both arms (never a
clarify, so the stage correctly stays out). Contractions ("What's")
are outside the four shapes. All three are documented in RESULTS.md.
