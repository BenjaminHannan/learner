#!/usr/bin/env python3
"""Experiment 174 -- THE ONE CHANGE: an "of"-phrased chain-question rewrite.

Director probe 08:55 on loop138f: after "Kim's boss is Lee." and "Lee's city
is Oslo.", the ask "What is the city of Kim's boss?" replies "I don't know
anyone called the city of Kim." -- wrong-shaped: FakeEars splits the
question body on "'s" only, so "the city of Kim" becomes the NAME and the
answer path reports an unknown entity instead of walking Kim -> boss -> city.

THE RULE (question-frame rewrite, ears only): before the unchanged base
hears the turn, rewrite exactly two frames:

  "What/Who is the R of X's S?"  ->  "What/Who is X's S's R?"
  "What/Who is the R of X?"      ->  "What/Who is X's R?"

and only when every content slot is closed-list safe:

  - R and S are single lowercase words in REL174 (the relation surfaces the
    base already recognises -- see below; anything else, e.g. "capital",
    "City", "King", "dean", passes through untouched);
  - X is a single capitalised name (``^[A-Z][A-Za-z]*$``; lowercase "kim",
    multi-word "the team", or compound "Zara's boss and Wren" never fire);
  - the turn is a question (exactly one terminal "?", no interior "?" / "!");
    statements ("the city of Kim's boss is Oslo.", "The city of Zara is
    Oslo.") are NEVER rewritten -- "of"-teaches stay exactly as they are
    (some are owned by bench73/158 -- left alone).

The candidate is used only when the UNCHANGED base parses it as a question
(an ask action); otherwise the original turn is heard unchanged. The stage
emits no actions of its own -- it returns the base's own ask list -- so an
"of"-ask writes exactly what its possessive twin writes (nothing: asks never
write). No existing file is edited.

Closed list REL174 (13 surfaces, read from the code, listed here):
  12 from scripts/fable_agent_loop.py PERSON_RELATIONS (the person relations
  FakeEars marks is_person): boss, brother, father, friend, husband, mother,
  neighbour, neighbor, partner, sister, teacher, wife.
  Plus "city": the non-person relation surface the base demonstrably stores
  and answers (director probe teach "Lee's city is Oslo." + possessive twin
  "What is Kim's boss's city?" -> "Kim's boss's city is Oslo.").
  FakeEars._relation() maps any surface to a key, but the rewrite fires only
  for these 13, so "capital", "king", "dean", "president", ... never rewrite.
"""

from __future__ import annotations

import re

# Closed list, read from the code (see module docstring). All lowercase.
REL174 = frozenset({
    "boss", "brother", "father", "friend", "husband", "mother",
    "neighbour", "neighbor", "partner", "sister", "teacher", "wife",
    "city",
})

_QWORD = r"(Who|What)"
_NAME = r"[A-Z][A-Za-z]*"
_REL = r"[a-z]+"

# 2-hop: "What is the city of Zara's boss?"
_TWOHOP_RE = re.compile(
    r"^\s*" + _QWORD + r"\s+is\s+the\s+(" + _REL + r")\s+of\s+(" + _NAME
    + r")'s\s+(" + _REL + r")\s*\?\s*$")
# 1-hop: "What is the city of Wren?"
_ONEHOP_RE = re.compile(
    r"^\s*" + _QWORD + r"\s+is\s+the\s+(" + _REL + r")\s+of\s+(" + _NAME
    + r")\s*\?\s*$")


def rewrite_chainof(turn: str) -> str | None:
    """Return the possessive-twin candidate, or None when no rewrite fires.

    None covers: statements (no terminal "?"), glued multi-sentence turns
    (interior "?" / "!"), non-Who/What frames, R/S outside REL174 or not
    lowercase, X not a single capitalised name, multi-word remainders.
    """
    text = " ".join(str(turn).split())
    if not text:
        return None
    work = text.replace("\u2019", "'")
    stem = work.rstrip()
    if not stem.endswith("?"):
        return None  # statements / bare fragments: never rewritten
    if ("?" in stem[:-1]) or ("!" in stem):
        return None  # glued turns: never spliced
    m = _TWOHOP_RE.match(work)
    if m is not None:
        qword, rel, name, sub = m.groups()
        if rel in REL174 and sub in REL174:
            return f"{qword} is {name}'s {sub}'s {rel}?"
        return None
    m = _ONEHOP_RE.match(work)
    if m is not None:
        qword, rel, name = m.groups()
        if rel in REL174:
            return f"{qword} is {name}'s {rel}?"
        return None
    return None


class ChainOf174Mixin:
    """Stackable outermost mixin: "of"-question rewrite before parsing.

    Cooperative (super() first on the candidate): hear() probes the
    unchanged base with the candidate and returns it iff the base parses
    the candidate as a question (an ask action); otherwise the original
    turn is heard unchanged. Side-effect free w.r.t. the notebook (the
    probe ask writes nothing; last_stage is overwritten by the final
    call), so the probe cannot change stored state.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        cand = rewrite_chainof(turn)
        if cand is not None and cand != " ".join(str(turn).split()):
            try:
                probe = super().hear(cand)  # type: ignore[misc]
            except Exception:
                probe = None
            if isinstance(probe, list) and any(
                    isinstance(a, dict) and a.get("act") == "ask"
                    for a in probe):
                try:
                    self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                        "loop174-chainof", 1.0)
                except AttributeError:
                    pass
                return probe
        return super().hear(turn)  # type: ignore[misc]
