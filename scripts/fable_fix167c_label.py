#!/usr/bin/env python3
"""Experiment 167c -- THE ONE CHANGE vs loop167b: Saved confirmations render
the relation with its human surface.

Director probe 08:57 on loop167b: "Ada was born in Paris." ->
"Saved: Ada's place_of_birth is Paris." while the answer path already says
"Ada's place of birth is Paris.". Root cause: the Saved text comes from the
notebook contract's TEMPLATES (scripts/fable_notebook_contract.py:77,
"Saved: {text}." with text built at :349 as
f"{subject}'s {relation} is {value}" using the RAW inventory key), while the
answer path renders spaces via FakeMouth.say's inline
`part.replace("_", " ")` (scripts/fable_agent_loop.py:166-167). NOT the same
one-line render function -- hence the mismatch.

THE ONE CHANGE (this file only; no 167b/167/162b/agent-loop/contract file
edited): the mouth -- the component whose job is "result record -> English"
-- applies the answer path's own surface rule (`key.replace("_", " ")`, the
exact expression FakeMouth.say uses on relation parts) to the relation slot
of Saved fact confirmations, for every relation key containing an
underscore. Stored facts, keys, and matching are untouched: the notebook
write already happened before the mouth runs, and the wrapper only
post-processes the outgoing English sentence.

Scope (deliberately narrow): ONLY `Saved: X's REL is V.` fact
confirmations move. CONFLICT / MISSING_FACT / Forgotten / clarify / answer
texts are returned byte-identical (answers already render spaces; the rest
are not confirmations). Non-underscore relations (city, employer, spouse)
match nothing and pass through byte-identical.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Saved fact confirmation: "Saved: {Name}'s {relation} is {value}."
# (notebook contract TEMPLATES[SAVED] + :349). The relation slot is a single
# key token (letters/digits/underscores); the value follows " is ".
_SAVED_RE = re.compile(
    r"^(Saved: .+?'s )([A-Za-z0-9_]+)( is .+\.)(\n?)$",
    re.DOTALL,
)


def render_saved_label(sentence: str) -> str:
    """Apply the answer path's surface rule to a Saved confirmation.

    Returns the sentence unchanged unless it is a `Saved: X's REL is V.`
    fact confirmation whose REL contains an underscore, in which case each
    underscore in REL becomes a space -- the same `part.replace("_", " ")`
    FakeMouth.say applies to answer-path relation parts. Pure string
    function: no notebook, no matching, no storage involved.
    """
    m = _SAVED_RE.fullmatch(sentence)
    if m is None:
        return sentence
    head, rel, tail, nl = m.group(1), m.group(2), m.group(3), m.group(4)
    if "_" not in rel:
        return sentence
    return f"{head}{rel.replace('_', ' ')}{tail}{nl}"


def saved_render_move(old: str, new: str) -> bool:
    """True when new == old (byte-identical) or new is old with exactly the
    Saved underscore-relation render applied (single trailing newline, if
    any, preserved). Shared by the 167c diff drivers so every suite judges
    reply moves by one rule.
    """
    if old == new:
        return True
    nl_o, nl_n = old.endswith("\n"), new.endswith("\n")
    if nl_o != nl_n:
        return False
    o, n = (old[:-1], new[:-1]) if nl_o else (old, new)
    m = _SAVED_RE.fullmatch(o)
    if m is None:
        return False
    head, rel, tail = m.group(1), m.group(2), m.group(3)
    if "_" not in rel:
        return False
    return n == f"{head}{rel.replace('_', ' ')}{tail}"


class Label167cMouth:
    """Stackable mouth wrapper: delegate, then render Saved labels.

    Cooperative: wraps any Mouth (the loop's own FakeMouth in practice);
    `say` delegates first so content words still come from the record only,
    then applies render_saved_label to the outgoing sentence. Reply text is
    the only thing that can change; records, events, keys, and matching are
    upstream and untouched.
    """

    name = "label167c-mouth"

    def __init__(self, inner) -> None:
        self.inner = inner

    def say(self, record: dict) -> str:
        return render_saved_label(self.inner.say(record))
