# 158c — wh-city question rewriter on loop158b (design)

One new file (`scripts/fable_loop158c_agent.py`) subclasses the frozen
loop158b agent. `Loop158cEars(Loop158bEars)` adds THE ONE CHANGE: a
question rewriter stage before the fallback. `turn()` is inherited
verbatim (L2 self layer untouched); `_act`, mouth, reasoner, sleeper,
daemon settle rule and atomic-write clients are exactly loop158b's.

## How it works

`hear()` runs the full loop158b stack first (`super().hear`, which
already includes the 158b whrel rewriter). If the base understood the turn
(anything but all-clarify), the result passes through untouched. Only
on an all-clarify do we try `rewrite_whcity(question, triples)`, then
run the rewrite through the base unchanged (`super().hear(newq)`) and
keep it only if it yields an ask; any teach/correct/forget2 in the
second pass is discarded, so questions never write.

`rewrite_whcity` is a pure function of (question, triples) mapping five
closed shapes onto the "Where does X live?" question the base answers:

- (e1) "What city does X live in?" / (e2) "Which city does X live in?"
- (e3) "What city is X in?" / (e4) "Which city is X in?"
- (e5) "What town does X live in?"

X may be a plain name ("Sue") or a possessive chain ("Kim's mother");
the entity gate is loop158b's own (`_ctx` / `_resolve_x` /
`chain_split` in `fable_loop158b_agent.py`, imported not copied): the
first chain segment must match a taught subject/object
(case-insensitive); every further hop must match a taught (subject,
relation) pair (last-wins). Unknown X passes through unchanged.

## Ordering and vetoes

The stage sits after everything in loop158b (158b whrel rewrite first)
and before the fallback (`fable_agent_loop.py:148,350`,
`fable_loop138_agent.py:81-93`), which it never edits. Canonical forms
("Where does Sue live?", "What is Sue's city?", "What city is Sue?")
never reach it because the base answers them. The four director
look-alikes match none of the five regexes by construction: "What city
is the capital of France?" has no trailing "in"; "What city are you
in?" uses "are" not "is"; "What city is best?" has no trailing "in";
"What city do you like?" is a different verb frame. A rewritten
question re-enters the base and is screened there, never answered
around.

## Known edges (measured on loop158b, not guessed)

"Where does Sue live?" answers "Sue's city is Leeds." and "Where does
Kim's mother live?" answers "Kim's mother's city is Oslo.", so the
rewrite inherits exact answers including 2-hop chains. A town-shaped
question ("What town does Bob live in?") answers through the city path
("Bob's city is Rome.") because the rewrite targets "Where does X
live?", which the base serves from the city relation. Unknown-X shapes
("What city is Zzz in?") clarify on both arms.
