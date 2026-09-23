#!/usr/bin/env python3
"""Exp 263 -- THE ONE CHANGE: no stored subject may contain a comma.

Base: the 260 arm (scripts/claude_loop260_agent.py, read-only). New file only.

GAP (director's held-out probe of 260): an unlisted opener ("Yo," + a
possessive teach) still stores the junk subject "Yo, X" on both 138m and
260. Listing openers cannot close this, because people keep inventing new
ones. Diagnosis from code reading, confirmed by the dev run on 260:
260's split_openers260 returns None for unlisted openers, so the turn
reaches the head unchanged, and 260's write guard only blocks subjects
that start with a LISTED opener + comma. The head then either
(a) parses the turn as a teach with a comma subject ("Yo, Kestrel's job
is fisher." stores "Yo, Kestrel"), or
(b) fails the shape entirely for multi-word openers ("Get this, Pell's
boss is Rhoda." stores nothing, answering "I couldn't save that...").
Both lose the fact; (a) also stores junk.

THE RULE (outermost, outside turn260):
  1. Guards (ears + _act, belt and braces): no teach/correct action whose
     subject contains a comma may pass, UNLESS the comma is name-internal:
     the tail after the comma starts with a title, ordinal, abbreviation
     or name particle ("Washington, D.C.", "Tony Hall, Baron Hall of
     Birkenhead", "William Morris, 1st Viscount Nuffield", "Hasbro,
     Inc."). Name-internal commas pass through exactly like 260, because
     bench chains teach and resolve such names. At the inner ears a
     blocked teach becomes the ears' own clarify (so the head gives its
     own save-failure reply); again at _act just before the write.
     Values are never guarded (a value can correctly hold a comma, e.g.
     "Tollan, Vesk"). Questions pass straight through with the guards on,
     so a question never writes and keeps 260's exact reply.
  2. turn263 runs the turn through the whole 260 head with the guard on.
     A clean write (no comma subject) is kept as-is: plain turns and
     comma values stay byte-identical to 260.
  3. If nothing was written, retry once on the text after the last comma
     of the leading segment (the turn up to its last comma is dropped),
     using the same head (the full turn260 stack). The retry runs when
     the guard blocked a comma-subject teach (case a), or when the head's
     reply to the turn is a clarify and the leading chunk is not a
     pretend/correction marker (case b: the head never parsed the opener
     turn at all). Save only if the retry writes with no comma in any
     stored subject. Otherwise the post-original state is restored and
     the head's own reply to the blocked turn stands (its save-failure
     reply) with 0 writes.
  4. No retry when the leading chunk (before the first comma) is a
     pretend/correction marker: bare "suppose"/"imagine"/"say"/"no"/
     "wait"/"sorry"/"anyhow", or a chunk starting with
     "suppose"/"imagine"/"say" + space. Stripping those would turn
     pretend into fact, which 260 deliberately never strips either.
  5. Single retry only: on multi-comma turns the last comma wins, so
     "Yo, Mara's boss is Wren, obviously." retries "obviously.", clarifies,
     and stores nothing (documented known limit, covered by a dev case).
     For appositives ("Tamsin, my baker, works at Fenwick.") the retry is
     the bare predicate ("works at Fenwick."), which the head clarifies,
     so nothing comma-subjected is ever stored.
  6. Fast paths (no snapshot overhead, byte-identical to 260): turns with
     no comma, bare greetings, and questions run straight through.

State: snapshots reuse 260's snapshot260/restore260 (imported read-only).
A retry that is not used is undone; the notebook event count decides
whether a save happened.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix260_openers as F260  # noqa: E402 (read-only helpers)

# Leading chunks that must never be stripped: bare pretend/correction
# markers, or suppose/imagine/say-led chunks (pretend-ambiguous).
_BARE_GUARD = set(F260.GUARD_ONLY260)
_PRETEND_LEAD = ("suppose", "imagine", "say")

# Name-internal commas: the tail after the comma starts with a title,
# ordinal, abbreviation or name particle, so the comma belongs to a real
# name ("Washington, D.C.", "Tony Hall, Baron Hall of Birkenhead",
# "William Morris, 1st Viscount Nuffield", "Hasbro, Inc."). These pass
# through exactly like 260. Anything else after the comma (a plain name
# like "Kestrel", "my"/"who" appositives) is opener-junk shaped.
_TITLE_TAIL_RE = re.compile(
    r"^(?:[A-Za-z]\.(?:[A-Za-z]\.)+|St\.|Jr\.?|Sr\.?|Inc\.?|Ltd\.?|Esq\.?|"
    r"Ph\.?D\.?|[0-9]+(?:st|nd|rd|th)\b|Baron(?:ess)?|Duke|Duchess|Earl|"
    r"Count(?:ess)?|Viscount(?:ess)?|Lord|Lady|Sir|Dame|Prince(?:ss)?|"
    r"King|Queen|Saint|of\b|de\b|von\b|van\b)")


def name_internal_comma263(text) -> bool:
    """The first comma looks name-internal (title/ordinal/abbrev tail)."""
    head, sep, tail = str(text).partition(",")
    if not sep or not head.strip():
        return False
    return bool(_TITLE_TAIL_RE.match(tail.strip()))


def has_comma_subject263(name) -> bool:
    """A subject holding a comma anywhere (the 263 junk shape)."""
    return "," in str(name or "")


def retry_text263(text: str):
    """Text after the last comma of the leading segment, else None."""
    t = str(text).strip()
    i = t.rfind(",")
    if i < 0:
        return None
    rest = t[i + 1:].strip()
    if not rest or not re.search(r"[A-Za-z0-9]", rest):
        return None
    return rest


def guarded_lead263(text: str) -> bool:
    """The leading chunk is a pretend/correction marker: never strip."""
    chunk = str(text).split(",", 1)[0].strip().lower()
    if chunk in _BARE_GUARD:
        return True
    return any(chunk.startswith(w + " ") for w in _PRETEND_LEAD)


def _is_teach(a) -> bool:
    return isinstance(a, dict) and a.get("act") in ("teach", "correct")


def _blocked(a) -> bool:
    return (_is_teach(a) and has_comma_subject263(a.get("name"))
            and not name_internal_comma263(a.get("name")))


CLARIFY_ACTION263 = dict(F260.CLARIFY_ACTION260)


def install_comma263(loop):
    """Install the 263 layer on a built 260 loop (outermost, instance)."""
    inner_turn = loop.turn            # turn260(turn224c(turn224(class turn)))
    loop.turn263_inner = inner_turn
    loop.comma263_log = []
    state = {"blocked": None, "subjects": []}

    # write guard at the inner ears (the head then gives its own reply)
    ears = getattr(loop, "_inner138j_ears", None)
    if ears is not None:
        ears_hear = ears.hear

        def hear263(turn, _h=ears_hear):
            acts = _h(turn)
            if isinstance(acts, list) and any(_blocked(a) for a in acts):
                state["blocked"] = [a for a in acts if _blocked(a)]
                loop.comma263_log.append({"guard": "ears", "turn": turn})
                return [dict(CLARIFY_ACTION263)]
            return acts

        ears.hear = hear263

    # write guard at _act (braces); records teach subjects for the retry check
    class_act = loop._act

    def act263(action, _a=class_act):
        if _is_teach(action):
            state["subjects"].append(str(action.get("name") or ""))
            if _blocked(action):
                state["blocked"] = [action]
                loop.comma263_log.append({"guard": "act",
                                          "act": action.get("act")})
                loop.counters["clarifications"] += 1
                return {"kind": "clarify",
                        "text": CLARIFY_ACTION263["text"]}
        return _a(action)

    loop._act = act263

    def turn263(text: str) -> list[str]:
        t = str(text)
        if "," not in t:
            return inner_turn(t)
        if F260.is_bare_greeting260(t):
            return inner_turn(t)
        if t.rstrip().endswith("?"):
            return inner_turn(t)    # questions: 260's reply, 0 writes
        s0 = F260.snapshot260(loop)
        e0 = F260._nb_events(loop)
        state["blocked"] = None
        state["subjects"] = []
        r0 = inner_turn(t)
        if F260._nb_events(loop) != e0:
            return r0                       # a clean write: keep it
        if state["blocked"] is not None:
            retry = retry_text263(t)        # comma-subject teach blocked
        elif (F260.is_clarify_reply260(r0)
                and not guarded_lead263(t)
                and not name_internal_comma263(t)):
            retry = retry_text263(t)        # head never parsed the turn
        else:
            return r0
        if not retry:
            return r0
        s1 = F260.snapshot260(loop)
        F260.restore260(s0)
        state["blocked"] = None
        state["subjects"] = []
        r1 = inner_turn(retry)
        wrote = F260._nb_events(loop) != e0
        subs = list(state["subjects"])
        if (wrote and state["blocked"] is None
                and not any("," in s for s in subs)):
            loop.comma263_log.append({"retry": retry})
            return r1
        F260.restore260(s1)
        return r0                           # head's save-failure reply, 0 writes

    turn263.__name__ = "turn263"
    loop.turn = turn263
    return loop
