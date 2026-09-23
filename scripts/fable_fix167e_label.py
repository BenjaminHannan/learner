#!/usr/bin/env python3
"""Experiment 167e -- THE ONE CHANGE vs loop167c: every reply template that
prints a relation key renders the 167c human surface (mouth only).

Director probe 09:10 on loop167c: "Forget Ada's place of birth." ->
"Forgotten: Ada's place_of_birth." and "Where was Ada born?" ->
"I don't know Ada's place_of_birth.". Root cause: loop167c
(scripts/fable_fix167c_label.py) renders ONLY the `Saved: X's REL is V.`
fact confirmation with the answer path's own surface rule
(`key.replace("_", " ")`, the exact expression FakeMouth.say uses at
scripts/fable_agent_loop.py:166-167); every other template that
interpolates the RAW inventory key still leaks it.

Reply templates that print a relation key, enumerated from the code
(the seal list; PASSMARKS.md quotes file:line for each):
  1. Saved fact confirmation -- scripts/fable_notebook_contract.py:77
     (TEMPLATES[SAVED]) with text built at :349
     (`f"{subject}'s {relation} is {value}"`) -- ALREADY fixed by 167c;
     this file keeps that behaviour byte-identical via the inner wrapper.
  2. CONFLICT change-prompt -- contract.py:79
     ("I have {subject}'s {relation} as {old}. Do you want me to change
     it to {new}?").
  3. MISSING_FACT "I don't know" -- contract.py:82
     ("I don't know {subject}'s {relation}.", via ask at :411-412 and via
     the forget-no-rows path at scripts/fable_listening_m1.py:143-144).
  4. BROKEN_CHAIN -- contract.py:83
     ("{subject}'s {relation} is {value}, which is not someone I can look
     up.", via ask at :405-407).
  5. Forgotten -- listening_m1.py:147
     ("Forgotten: {entity}'s {relation}.").
Already clean (no change, enumerated so the seal is complete):
  6. Answer path -- agent_loop.py:166-167 already renders
     `part.replace("_", " ")` on every relation part.
  7. Clarifies -- agent_loop.py:115,126-127,139,142,144,148,350,367 and
     listening_m1.py:78,157,163,166 are fixed strings with no relation
     slot (the "(I dropped my earlier question.) " note at
     listening_m1.py:78 is a prefix only).
  8. AMBIGUOUS (:80), UNKNOWN_ENTITY (:81), DUPLICATE_OK (:78),
     NOT_ALLOWED (:86), BAD_REQUEST (:87) -- no relation slot.
  9. Internal Saved texts that never reach the mouth: declare_relation
     "Saved: relation {relation}." (contract.py:266, return value ignored
     at listening_m1.py:60-63), retract "forgot {fact_id}" (:362,
     superseded by the Forgotten text), entity/alias/rule/merge texts
     (:277,:286,:294,:387, no relation slots).

THE ONE CHANGE (this file only; no 167c/167b/167/162b/agent-loop/
contract/listening file edited): the mouth -- result record -> English
-- applies the answer path's own surface rule (`key.replace("_", " ")`)
to the relation slot of templates 2-5 (template 1 is already spaced by
the inner loop167c mouth; re-applying it here is idempotent), for every
relation key containing an underscore, with an optional
"(I dropped my earlier question.) " prefix tolerated. Stored facts,
keys, matching, and which reply is chosen are untouched: the notebook
write already happened before the mouth runs, and the wrapper only
post-processes the outgoing English sentence.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix167c_label as C167C  # noqa: E402 (Saved render, read-only)

# Listening may prefix any reply with its dropped-question note
# (scripts/fable_listening_m1.py:78).
_DROPPED = r"(?:\(I dropped my earlier question\.\) )?"

_MISSING_RE = re.compile(
    _DROPPED + r"I don't know (.+?)'s (\S+)\.$",
    re.DOTALL,
)
_CONFLICT_RE = re.compile(
    _DROPPED + r"I have (.+?)'s (\S+) as (.+)\. Do you want me to "
    r"change it to (.+)\?$",
    re.DOTALL,
)
_BROKEN_RE = re.compile(
    _DROPPED + r"(.+?)'s (\S+) is (.+), which is not someone I can "
    r"look up\.$",
    re.DOTALL,
)
_FORGOTTEN_RE = re.compile(
    _DROPPED + r"Forgotten: (.+?)'s (\S+)\.$",
    re.DOTALL,
)


def _space_rel(slot: str) -> str:
    """The answer path's own surface rule (agent_loop.py:166-167)."""
    return slot.replace("_", " ")


def render_label(sentence: str) -> str:
    """Apply the 167c surface rule to every relation-key reply template.

    Returns the sentence unchanged unless it is a Saved / MISSING /
    CONFLICT / BROKEN / Forgotten template whose relation slot contains
    an underscore, in which case each underscore in that slot -- and
    only that slot -- becomes a space. Pure string function: no
    notebook, no matching, no storage involved.
    """
    out = C167C.render_saved_label(sentence)
    if out != sentence:
        return out
    nl = "\n" if out.endswith("\n") else ""
    body = out[:-1] if nl else out

    m = _MISSING_RE.fullmatch(body)
    if m is not None and "_" in m.group(2):
        return f"{m.group(0)[:m.start(2)]}{_space_rel(m.group(2))}.{nl}"
    m = _FORGOTTEN_RE.fullmatch(body)
    if m is not None and "_" in m.group(2):
        return f"{m.group(0)[:m.start(2)]}{_space_rel(m.group(2))}.{nl}"
    m = _CONFLICT_RE.fullmatch(body)
    if m is not None and "_" in m.group(2):
        return (f"{m.group(0)[:m.start(2)]}{_space_rel(m.group(2))}"
                f" as {m.group(3)}. Do you want me to change it to "
                f"{m.group(4)}?{nl}")
    m = _BROKEN_RE.fullmatch(body)
    if m is not None and "_" in m.group(2):
        return (f"{m.group(0)[:m.start(2)]}{_space_rel(m.group(2))}"
                f" is {m.group(3)}, which is not someone I can look up."
                f"{nl}")
    return sentence


def label_render_move(old: str, new: str) -> bool:
    """True when new == old (byte-identical) or new is old with exactly
    one relation-slot render applied (single trailing newline, if any,
    preserved). Shared by the 167e diff drivers so every suite judges
    reply moves by one rule."""
    if old == new:
        return True
    nl_o, nl_n = old.endswith("\n"), new.endswith("\n")
    if nl_o != nl_n:
        return False
    o, n = (old[:-1], new[:-1]) if nl_o else (old, new)
    if C167C.saved_render_move(o, n):
        return True
    return render_label(o) == n and render_label(o) != o


class Label167eMouth:
    """Stackable mouth wrapper: delegate, then render relation labels.

    Cooperative: wraps any Mouth (loop167c's mouth in practice, which
    already spaces Saved lines); `say` delegates first so content words
    still come from the record only, then applies render_label to the
    outgoing sentence. Reply text is the only thing that can change;
    records, events, keys, and matching are upstream and untouched.
    """

    name = "label167e-mouth"

    def __init__(self, inner) -> None:
        self.inner = inner

    def say(self, record: dict) -> str:
        return render_label(self.inner.say(record))
