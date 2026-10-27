#!/usr/bin/env python3
"""Exp 281 -- THE ONE CHANGE: "What is Ana's cat called?" reads as "What is Ana's cat?".

Base: 260 (scripts/claude_loop260_agent.py, read-only). New file only.

DIAGNOSIS (reproduced live on 260; the probe's own rows are
artifacts/claude-chatweak-20260923/dialogs.json t04-t5 and t12-t4):
  - "What is Rosa's dog called?" (Rosa/dog/Pip stored) gets
    "I don't know Rosa's dog called." -- a malformed abstain -- while the
    plain "What is Rosa's dog?" gets "Rosa's dog is Pip.".
  - Same for "named": "What is Tomas's boat named?" (stored) gets
    "I don't know Tomas's boat named.".
  - "What do you call Ivo's band?" (stored) gets the clarify line
    ("I didn't understand that question ...").
  - "What's the name of Rosa's street?" / "What is the name of Pell's
    teacher?" (stored) get "I don't know anyone called the name of Rosa."
    (a lookup of "the name of Rosa" as a person).
  - "Who is Ana's cat called?" (stored) gets the same broken abstain as
    the "What is" form; plain "Who is Ana's cat?" answers correctly.
  - Never-taught subjects already abstain honestly
    ("What is Zara's dog called?" -> "I don't know anyone called Zara.");
    those must keep abstaining (0 new guesses).
  - "Who is Rosa's friend called Bo?" ("called" belongs to the value/name)
    abstains on 260; it must keep 260's route exactly (no rewrite applies:
    "called" is not trailing).

THE RULE (outermost instance turn wrapper turn281 over turn260, question
turns only):
  1. Only turns ending in "?" are candidates. Teach turns and writes are
     untouched (the turn runs exactly as 260 runs it).
  2. A trailing "called" / "named" after a relation phrase, "what do you
     call X?", and "what's / what is the name of X?" are rewritten to the
     plain possessive question ("What is X's R?"; the wh-word is kept, so
     "Who is X's R called?" becomes "Who is X's R?"). An opener prefix
     ("So, ...") is kept on the rewritten turn, so 260's own opener layer
     handles it. "called <Name>" (a name after called) never matches, so
     ambiguous value-questions keep 260's route byte-identical.
  3. The original turn runs first through the whole head. If it already
     answers (not a clarify, not an abstain), its reply stands. Else the
     rewritten turn runs as if typed alone. Its reply is used only if it
     answers AND the run wrote nothing (questions never write; a written
     run is undone and the original stands). Otherwise the state after the
     original run is restored and the original reply stands. Net effect:
     the only moves are called-wording + stored fact -> the exact answer;
     everything else is byte-identical to 260, with identical stores.
"""

from __future__ import annotations

import re

import claude_fix260_openers as F260  # noqa: E402 (read-only helpers)


def _apos(t: str) -> str:
    return t.replace("\u2019", "'").replace("\u2018", "'")


# Question-wording patterns (matched on the core after an optional opener
# prefix; IGNORECASE; "?" required at the end). Group "rel" is the
# relation phrase; group "wh" keeps who/what.
_PATTERNS281 = (
    ("trailing", re.compile(
        r"^(?P<wh>who|what)\s+is\s+(?P<rel>.+?)\s+"
        r"(?P<tail>called|named)\s*\?+\s*$", re.IGNORECASE)),
    ("doyoucall", re.compile(
        r"^what\s+do\s+you\s+call\s+(?P<rel>.+?)\s*\?+\s*$",
        re.IGNORECASE)),
    ("nameof", re.compile(
        r"^what(?:'s|s|\s+is)\s+the\s+name\s+of\s+(?P<rel>.+?)\s*\?+\s*$",
        re.IGNORECASE)),
)


def rewrite_called281(text: str):
    """Return the plain-question rewrite of a called/named question turn,
    else None. Keeps any opener prefix on the rewritten turn."""
    t = _apos(str(text))
    if not t.rstrip().endswith("?"):
        return None
    core = t.strip()
    prefix = ""
    m, kind = _match_core(core)
    if m is None:
        sp = F260.split_openers260(t)
        if sp is None:
            return None
        rest = sp[0]
        m, kind = _match_core(rest.strip())
        if m is None:
            return None
        rstrip = t.rstrip()
        core_stripped = rest.strip()
        if not core_stripped or not rstrip.endswith(core_stripped):
            return None
        prefix = rstrip[:len(rstrip) - len(core_stripped)]
        core = core_stripped
    if kind == "trailing":
        wh = m.group("wh")
        wh = "Who" if wh.lower() == "who" else "What"
        return prefix + "%s is %s?" % (wh, m.group("rel").strip())
    # "what do you call X?" / "name of X?" -> "What is X?"
    return prefix + "What is %s?" % (m.group("rel").strip())


def _match_core(core: str):
    for kind, rx in _PATTERNS281:
        m = rx.match(core)
        if m is not None and m.group("rel").strip():
            return m, kind
    return None, None


# A reply that did NOT answer (clarify glue or honest abstain). Anything
# else counts as an answer.
_CLARIFY281 = F260.CLARIFY_MARKS260 + ("was that a question",)
_DONTKNOW281 = ("don't know", "do not know", "never told me",
                "never taught me", "no record",
                "not someone i can look up")


def is_answer281(reply_lines) -> bool:
    text = " ".join(str(x) for x in (reply_lines or [])).lower()
    if not text.strip():
        return False
    if any(m in text for m in _CLARIFY281):
        return False
    return not any(m in text for m in _DONTKNOW281)


def install_called281(loop):
    """Install the 281 layer on a built 260 loop (outermost, instance)."""
    inner_turn = loop.turn            # turn260(turn224c(...))
    loop.turn281_inner = inner_turn
    loop.called281_log = []

    def turn281(text: str) -> list[str]:
        t = str(text)
        rw = rewrite_called281(t)
        if rw is None or rw == t:
            return inner_turn(t)
        s0 = F260.snapshot260(loop)
        e0 = F260._nb_events(loop)
        r0 = list(inner_turn(t))
        if F260._nb_events(loop) != e0:
            return r0                 # a write: keep the original
        if is_answer281(r0):
            return r0                 # already answered: keep it
        s1 = F260.snapshot260(loop)
        F260.restore260(s0)
        r1 = list(inner_turn(rw))
        wrote = F260._nb_events(loop) != e0
        if wrote or not is_answer281(r1):
            F260.restore260(s1)
            return r0                 # rewrite failed: 260's route stands
        loop.called281_log.append({"turn": t, "rewritten": rw})
        return r1

    turn281.__name__ = "turn281"
    loop.turn = turn281
    return loop
