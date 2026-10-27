#!/usr/bin/env python3
"""Exp 266 THE ONE CHANGE: chain-subject lift for two-step questions.

Diagnosis (design/v3/30-modes/266-chain-subject-questions.md): the notebook
and the chain reasoner already answer "Ana's boss's city" (possessive
chains), but the verb / "when" question readers (167, 167d, the base
"where does X live" reader, ...) only accept a SINGLE name as the subject.
A possessive chain in that slot ("Where does Ana's boss live?") misses
every reader and the turn falls through to "I didn't understand that
question."

266 = base (138m) + ONE outermost ears stage, "chain-subject lift", for
questions only. When a question ending in "?" holds a possessive chain as
its subject ("A's R1", "A's R1's R2", "my R1", "my R1's R2"):
  1. Swap the chain for one placeholder name that is not in the notebook
     and hear that rewritten question through the whole existing stack in
     a dry, write-free way (the 221c pattern: only when it gives exactly
     one one-hop ask frame, with relation R and the placeholder as
     subject, and no write act).
  2. Then hear the canonical possessive question "What is <chain>'s R?"
     (for a person-valued R: "Who is <chain>'s R?") through the whole
     stack, and serve that reply. The base reasoner already answers it,
     gives "I don't know ..." when a link is missing, and never writes.
  3. In every other case the turn passes through byte-identical.

It does not add new verb phrasings: "What does X do?" fails for plain
names too and stays out of 266 (the placeholder probe clarifies, so the
gate fails and the turn passes through).

New file only; every base module is imported read-only. The mixin owns no
save code, no ask code and no screens.
"""

from __future__ import annotations

import json
import os
import re

PLACEHOLDER266 = "Zqbex"  # single capital-lead token; passes _subject_ok

# Person-valued relations take "Who is <chain>'s R?", the rest "What is ...".
# PERSON_RELATIONS mirrors scripts/fable_agent_loop.py; employer uses "Who"
# (the established verb167 twin "Who is X's employer?").
PERSON266 = frozenset({
    "mother", "father", "sister", "brother", "friend", "boss", "teacher",
    "wife", "husband", "neighbour", "neighbor", "partner", "employer",
})

_WRITE_FREE266 = frozenset({"ask", "clarify", "answer"})

_APOS266 = r"['\u2019]"
_MY266 = r"[Mm][Yy]"
_NAME266 = r"[A-Z][A-Za-z'\u2019\-]*"
_REL266 = r"[A-Za-z][A-Za-z\-]*"
_LINK266 = r"(?:" + _APOS266 + r"s " + _REL266 + r")"
# Longest chain first: greedy links take "Ana's boss's city" whole (so a
# possessive question collapses to "What is Zqbex?" -> clarify -> pass
# through), while a verb question keeps only the link part ("Ana's boss").
# "my" takes a bare first relation ("my boss"), a name takes 's links.
CHAIN266_RE = re.compile(
    r"(?:" + _MY266 + r" " + _REL266 + _LINK266 + r"{0,2}"
    r"|" + _NAME266 + _LINK266 + r"{1,3})")

STAGE266 = "loop266-chainlift"


def find_chain266(turn: str) -> tuple[str, int, int] | None:
    """Longest possessive-chain span in a ?-turn, else None.

    Returns (chain, start, end). Open relation vocabulary: the probe gate
    (exactly one one-hop ask frame for the placeholder) decides whether
    the turn is lifted, so a wrong span can only pass the turn through.
    """
    t = " ".join(str(turn).split())
    if not t.endswith("?"):
        return None
    m = CHAIN266_RE.search(t)
    if m is None:
        return None
    return (m.group(0), m.start(), m.end())


def placeholder_in_notebook266(ears, placeholder: str = PLACEHOLDER266) -> bool:
    """True when the placeholder is a known name (then never lift)."""
    try:
        nb = getattr(ears, "nb", None)
        if nb is None:
            return False
        import fable_loop90_agent as L90  # noqa: E402 (read-only)
        names = set()
        for triple in L90.notebook_triples(nb):
            try:
                names.add(triple[0])
            except Exception:
                continue
        return placeholder in names
    except Exception:
        return False


def gate266(acts, placeholder: str = PLACEHOLDER266) -> str | None:
    """One-hop ask check on dry-heard acts; relation R or None.

    Accepts only: a list of exactly one ask frame, subject == placeholder,
    exactly one (one-hop) relation, and no write act anywhere.
    """
    if not isinstance(acts, list) or len(acts) != 1:
        return None
    if any(not isinstance(a, dict) or a.get("act") not in _WRITE_FREE266
           for a in acts):
        return None
    frame = acts[0]
    if frame.get("act") != "ask":
        return None
    if frame.get("name") != placeholder:
        return None
    rels = frame.get("relations")
    if not isinstance(rels, list) or len(rels) != 1 \
            or not isinstance(rels[0], str) or not rels[0]:
        return None
    return rels[0]


def canonical266(chain: str, relation: str) -> str:
    """Canonical possessive question for a lifted chain + relation R."""
    surface = "_".join(str(relation).strip().lower().split())
    surface = surface.replace("_", " ")
    wh = "Who" if str(relation).strip().lower() in PERSON266 else "What"
    return f"{wh} is {chain}'s {surface}?"


def plan266(turn: str) -> tuple[str, str] | None:
    """Chain + placeholder-swapped question for a ?-turn, else None.

    Pure text step (no hear). The mixin then dry-hears the rewritten
    question and only lifts when gate266 accepts exactly one one-hop ask
    frame for the placeholder.
    """
    if PLACEHOLDER266 in str(turn):
        return None
    found = find_chain266(turn)
    if found is None:
        return None
    chain, start, end = found
    t = " ".join(str(turn).split())
    rewritten = t[:start] + PLACEHOLDER266 + t[end:]
    return (chain, rewritten)


class ChainLift266Mixin:
    """Outermost ears stage: chain-subject lift (questions only, never writes)."""

    last_chainlift266: dict | None = None

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        self.last_chainlift266 = None
        try:
            plan = plan266(turn)
        except Exception:  # noqa: BLE001 -- lift never breaks a turn
            plan = None
        if plan is not None and not placeholder_in_notebook266(self):
            chain, rewritten = plan
            try:
                probe = super().hear(rewritten)  # type: ignore[misc]
            except Exception:
                probe = None
            relation = gate266(probe) if probe is not None else None
            if relation is not None:
                canonical = canonical266(chain, relation)
                try:
                    acts = super().hear(canonical)  # type: ignore[misc]
                except Exception:
                    return super().hear(turn)  # type: ignore[misc]
                if isinstance(acts, list):
                    self.last_chainlift266 = {"turn": turn,
                                              "canonical": canonical}
                    log = os.environ.get("CHAINLIFT266_LOG")
                    if log:
                        try:
                            with open(log, "a", encoding="utf-8") as fh:
                                fh.write(json.dumps(
                                    {"turn": turn,
                                     "canonical": canonical}) + "\n")
                        except OSError:
                            pass
                    return acts
        return super().hear(turn)  # type: ignore[misc]


def selftest266() -> int:
    """Pure-function checks: detection spans + canonical phrasing."""
    ok = True

    def check(turn, want_chain):
        nonlocal ok
        got = find_chain266(turn)
        good = (got is None and want_chain is None) or (
            got is not None and want_chain is not None
            and got[0] == want_chain)
        ok = ok and good
        print(f"{'OK' if good else 'MISMATCH'}: {turn!r} -> "
              f"{(got[0] if got else None)!r} (want {want_chain!r})")

    check("Where does Vex's boss live?", "Vex's boss")
    check("Where does Pix's boss's boss live?", "Pix's boss's boss")
    check("Where does my teacher live?", "my teacher")
    check("Who does my brother's boss work for?", "my brother's boss")
    check("What is Ana's boss's city?", "Ana's boss's city")
    check("Who is Ana's boss's employer?", "Ana's boss's employer")
    check("Where does Tovi live?", None)
    check("What town does Tovi live in?", None)
    check("Vex's boss is Quil.", None)
    check("What does Tovi do?", None)
    check("Where does Ana’s boss live?", "Ana’s boss")

    def check_canon(chain, rel, want):
        nonlocal ok
        got = canonical266(chain, rel)
        good = got == want
        ok = ok and good
        print(f"{'OK' if good else 'MISMATCH'}: ({chain!r}, {rel!r}) -> "
              f"{got!r} (want {want!r})")

    check_canon("Vex's boss", "city", "What is Vex's boss's city?")
    check_canon("Wex's sister", "employer", "Who is Wex's sister's employer?")
    check_canon("Fex's father", "place_of_birth",
                "What is Fex's father's place of birth?")
    check_canon("Yara's friend", "language",
                "What is Yara's friend's language?")
    check_canon("my teacher", "city", "What is my teacher's city?")
    check_canon("Ana's boss", "boss", "Who is Ana's boss's boss?")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(selftest266())
