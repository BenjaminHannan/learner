"""Agent 4 (WIRING) -- the 40-turn scripted conversation and its expected outcomes.

Composition (checked by ``check_composition``):
    15 teaching turns   (12 statements incl. 1 correction + create-2nd-Mira +
                         1 ambiguous statement + its pick)  -> 13 fact rows
    15 question turns   (6 one-hop, 6 two-hop, 3 unanswerable)
     5 hearsay/trap sentences   (must write nothing)
     5 small-talk turns         (must write nothing)

Every turn carries the expected notebook effect, so the replay can count taught
rows, wrong writes (must be 0), correct answers and abstentions turn by turn.
``@mira:0`` expands at run time to the entity id of the FIRST person called Mira
(the second one is created by turn "person: Mira").
"""

from __future__ import annotations

import re

TEACH, CREATE, AMBIG, PICK = "teach", "create_second_mira", "teach_ambiguous", "pick"
ONE_HOP, TWO_HOP, UNANSWERABLE, TRAP, SMALLTALK = (
    "one_hop", "two_hop", "unanswerable", "trap", "smalltalk")

# expected effect of a teaching turn: (subject, relation, value, correction?)
EXPECTED_FACT = "fact"

TURNS: list[dict] = [
    # ---------------------------------------------------------------- teaching (15)
    dict(kind=TEACH, text="Mira's city is Lisbon.",
         expect=dict(fact=("Mira", "city", "Lisbon", False))),
    dict(kind=TEACH, text="Mira's mother is Ana.",
         expect=dict(fact=("Mira", "mother", "Ana", False))),
    dict(kind=TEACH, text="Kai's sister is Mira.",
         expect=dict(fact=("Kai", "sibling", "Mira", False))),
    dict(kind=TEACH, text="Actually, Mira's city is Paris.",
         expect=dict(fact=("Mira", "city", "Paris", True))),
    dict(kind=TEACH, text="Ana's city is Porto.",
         expect=dict(fact=("Ana", "city", "Porto", False))),
    dict(kind=TEACH, text="Ana's father is Tom.",
         expect=dict(fact=("Ana", "father", "Tom", False))),
    dict(kind=TEACH, text="Ana's friend is Tom.",
         expect=dict(fact=("Ana", "friend", "Tom", False))),
    dict(kind=TEACH, text="Tom's city is Rome.",
         expect=dict(fact=("Tom", "city", "Rome", False))),
    dict(kind=TEACH, text="Tom's friend is Ana.",
         expect=dict(fact=("Tom", "friend", "Ana", False))),
    dict(kind=TEACH, text="Tom's father is Sam.",
         expect=dict(fact=("Tom", "father", "Sam", False))),
    dict(kind=TEACH, text="Sam's city is Faro.",
         expect=dict(fact=("Sam", "city", "Faro", False))),
    dict(kind=TEACH, text="Kai's city is Oslo.",
         expect=dict(fact=("Kai", "city", "Oslo", False))),
    dict(kind=CREATE, text="person: Mira",
         expect=dict(entities=1)),
    dict(kind=AMBIG, text="Mira's origin is Athens.",
         expect=dict(fact=None)),                     # ambiguous: writes until the pick
    dict(kind=PICK, text="@mira:0",
         expect=dict(fact=("Mira", "origin", "Athens", False))),

    # ------------------------------------------------------------- questioning (15)
    dict(kind=ONE_HOP, text="Where is Ana's city?", expect=dict(answer="Porto")),
    dict(kind=ONE_HOP, text="Who is Ana's father?", expect=dict(answer="Tom")),
    dict(kind=ONE_HOP, text="Where is Tom's city?", expect=dict(answer="Rome")),
    dict(kind=ONE_HOP, text="Who is Tom's friend?", expect=dict(answer="Ana")),
    dict(kind=ONE_HOP, text="Where is Sam's city?", expect=dict(answer="Faro")),
    dict(kind=ONE_HOP, text="Where is Kai's city?", expect=dict(answer="Oslo")),
    dict(kind=TWO_HOP, text="Where is Ana's friend's city?", expect=dict(answer="Rome")),
    dict(kind=TWO_HOP, text="Where is Kai's sibling's city?", expect=dict(answer="Paris")),
    dict(kind=TWO_HOP, text="Who is Ana's father's friend?", expect=dict(answer="Ana")),
    dict(kind=TWO_HOP, text="Where is Tom's friend's city?", expect=dict(answer="Porto")),
    dict(kind=TWO_HOP, text="Who is Ana's friend's father?", expect=dict(answer="Sam")),
    dict(kind=TWO_HOP, text="Who is Ana's father's father?", expect=dict(answer="Sam")),
    dict(kind=UNANSWERABLE, text="Where is Zed's city?",
         expect=dict(abstain="don't know anyone")),
    dict(kind=UNANSWERABLE, text="Where is Ana's city's mother?",
         expect=dict(abstain="not someone I can look up")),
    dict(kind=UNANSWERABLE, text="Where is Kai's maternal grandmother?",
         expect=dict(abstain=("don't know", "didn't trust that parse"))),

    # ------------------------------------------------------- hearsay / traps (5)
    dict(kind=TRAP, text="Tom said Mira's city is Oslo.", expect=dict()),
    dict(kind=TRAP, text="I heard Mira's mother is Kira.", expect=dict()),
    dict(kind=TRAP, text="According to Ana, Mira's city is Rome.", expect=dict()),
    dict(kind=TRAP, text="If Mira's city were Rome, she would smile.", expect=dict()),
    dict(kind=TRAP, text="Mira told me her city is Faro.", expect=dict()),

    # ----------------------------------------------------------- small talk (5)
    dict(kind=SMALLTALK, text="Hi, how are you?", expect=dict()),
    dict(kind=SMALLTALK, text="Thanks, that helps.", expect=dict()),
    dict(kind=SMALLTALK, text="What's the weather like today?", expect=dict()),
    dict(kind=SMALLTALK, text="Tell me a joke.", expect=dict()),
    dict(kind=SMALLTALK, text="Good morning!", expect=dict()),
]

PICK_PATTERN = re.compile(r"^@([^:]+):(\d+)$")


def expand(text: str, aliases: dict) -> str:
    """``@name:k`` -> the k-th entity id registered under that alias."""
    m = PICK_PATTERN.match(text.strip())
    if not m:
        return text
    ids = aliases.get(m.group(1).lower(), [])
    if not ids:
        raise KeyError(f"no entity aliased {m.group(1)!r}")
    return f"pick {ids[int(m.group(2))]}"


def counts() -> dict:
    kinds: dict[str, int] = {}
    for turn in TURNS:
        kinds[turn["kind"]] = kinds.get(turn["kind"], 0) + 1
    return kinds


def check_composition() -> list[tuple[str, bool, str]]:
    k = counts()
    teaching = sum(k.get(x, 0) for x in (TEACH, CREATE, AMBIG, PICK))
    asking = sum(k.get(x, 0) for x in (ONE_HOP, TWO_HOP, UNANSWERABLE))
    expected_facts = sum(1 for t in TURNS
                         if t["expect"].get("fact") and t["kind"] != AMBIG)
    checks = [
        ("40 turns", len(TURNS) == 40, f"got {len(TURNS)}"),
        ("15 teaching turns", teaching == 15, f"got {teaching}"),
        ("15 question turns", asking == 15, f"got {asking}"),
        ("5 traps", k.get(TRAP, 0) == 5, f"got {k.get(TRAP, 0)}"),
        ("5 small talk", k.get(SMALLTALK, 0) == 5, f"got {k.get(SMALLTALK, 0)}"),
        ("1 correction", sum(1 for t in TURNS
                             if t["expect"].get("fact") and t["expect"]["fact"][3]) == 1, ""),
        ("1 ambiguous teach + pick", k.get(AMBIG, 0) == 1 and k.get(PICK, 0) == 1, ""),
        ("6 two-hop (>=3)", k.get(TWO_HOP, 0) >= 3, f"got {k.get(TWO_HOP, 0)}"),
        ("3 unanswerable", k.get(UNANSWERABLE, 0) == 3, f"got {k.get(UNANSWERABLE, 0)}"),
        ("13 fact rows expected", expected_facts == 13, f"got {expected_facts}"),
    ]
    return checks


if __name__ == "__main__":
    bad = 0
    for name, ok, note in check_composition():
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{note}]" if note and not ok else ""))
        bad += not ok
    raise SystemExit(1 if bad else 0)
