# 174 — "of"-phrased chain questions (Muse, on loop138f)

## Problem

Director probe on loop138f: after "Kim's boss is Lee." and "Lee's city is
Oslo.", the ask "What is the city of Kim's boss?" replies "I don't know
anyone called the city of Kim.". FakeEars splits the question body on "'s"
only, so "the city of Kim" becomes the entity NAME and the lookup reports
an unknown entity instead of walking Kim -> boss -> city. The possessive
twin "What is Kim's boss's city?" answers correctly, so the knowledge and
the hop loop are fine — only the question frame is uncovered.

## Fix (ears only, one change)

`scripts/fable_fix174_chainof.py` adds an outermost ears stage that rewrites
exactly two question frames before the unchanged base hears the turn:

- "What/Who is the R of X's S?" -> "What/Who is X's S's R?" (2-hop)
- "What/Who is the R of X?" -> "What/Who is X's R?" (1-hop)

Fire conditions (all must hold): the turn ends in exactly one "?" with no
interior "?" / "!"; R and S are single lowercase words in REL174; X matches
`^[A-Z][A-Za-z]*$`. The candidate is then heard by the unchanged base and
kept only if it parses as an ask; otherwise the original passes through.
The stage returns the base's own ask list, so an "of"-ask writes exactly
what its twin writes (nothing). Statements are never eligible, so
"of"-teaches (some owned by bench73/158) are untouched.

REL174 (13, read from the code): boss, brother, father, friend, husband,
mother, neighbour, neighbor, partner, sister, teacher, wife (the 12
PERSON_RELATIONS in `scripts/fable_agent_loop.py`) + city (the non-person
surface the base demonstrably stores: the probe teach "Lee's city is Oslo."
plus the correct possessive-twin answer). FakeEars._relation maps any
surface, but the rewrite fires only for these 13, so "capital", "king",
"dean", "president" and friends can never rewrite — that is what makes the
traps ("What is the City of London?", "Who is the King of Spain?", "What is
the capital of France?") safe by construction, as are lowercase names,
compounds, non-names, and mark-less turns (all fail the shape).

## Stack

`scripts/fable_loop174_agent.py`: Loop174Ears (ChainOf174Mixin outermost
over Loop138fEars) + Loop138fAgentLoop inherited verbatim + the same
reasoner/notebook/sleeper/thinker/settle pieces via the 138f build shape.
No existing file edited.

## Verification

T1 (40-turn sealed file: 6 teaches, 12 of-asks with possessive twins, 10
traps): 12/12 twin-equal, 8/8 taught exact, 4/4 untaught honest
("I don't know …"), 10/10 traps byte-identical, 0 ask writes, script
identical except the 12 predicted moves. T2: redteam136/143, sessions152,
bench 800, marks123 all per-case identical to loop138f except the single
predicted sleep-reason filename line; 0 new WRONG anywhere. Pre-seal
pure-function scan found 0 rewrite firings in 1498 frozen-suite inputs.

## Limits

Only 1- and 2-hop "is" frames with closed-list relations; "capital of …",
multi-word remainders, and relative clauses still clarify. Reverse
("Whose …") stays with exp 153. No statement coverage is attempted on
purpose.
