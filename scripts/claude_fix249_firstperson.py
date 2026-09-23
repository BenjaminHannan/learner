#!/usr/bin/env python3
"""Experiment 249 -- THE ONE CHANGE (cause D of diagnosis 243): first-person
twins.

FirstPerson249Mixin sits OUTERMOST on the ears and only rewrites a question
about the user into the "my" form that Me166 (scripts/fable_fix166_me.py)
already answers:

    "Where do I live?"        -> "What is my city?"
    "Who am I married to?"    -> "Who is my spouse?"
    "What's my X?"            -> "What is my X?"
    "Where do I work?" / "Who do I work for?" -> "Who is my employer?"
    (plus the other verb forms in MAP249 below)

Gates (all must hold, otherwise the ORIGINAL turn goes to the base ears
untouched, byte-identical to base228):
  1. the turn ends in "?" and contains I / me / my (whole word);
  2. it fully matches one of the patterns below (optional greeting lead and
     optional "please");
  3. the target relation is STORED for the user (USER entity, active taught
     fact). For a verb form with several candidate relations, exactly ONE
     candidate must be stored; zero or two+ -> no rewrite (honest decline
     stays). For "What's my a's b?" every link of the chain must resolve;
  4. the base ears, given the rewritten text, return exactly one read-only
     Me166 ask (me166 True, act "ask", name USER). Anything else -> the
     original turn is heard instead.
Statements never reach this code, so no write path changes. The rewritten
ask is read-only, so a question never writes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (apostrophe splitter, read-only)
import fable_fix166_me as M166  # noqa: E402 (USER key + relation keys, read-only)
import fable_loop166_agent as L166  # noqa: E402 (me reply renderer, read-only)
import fable_loop90_agent as L90  # noqa: E402 (value display, read-only)

STAGE249 = "loop249-firstperson"
USER249 = M166.USER_KEY

# Optional lead / tail words that carry no meaning for the lookup.
_LEAD = r"(?:(?:hi|hello|hey|ok|okay|so)\s*[,!.]?\s+)?(?:please\s*,?\s+)?"
_TAIL = r"(?:\s*,?\s+(?:please|now|currently|these\s+days|again))?"

# MAP249: (pattern body, candidate relations in the notebook's own keys,
# wh-word of the rewritten "my" form). Declared in PASSMARKS.md too.
MAP249: list[tuple[str, tuple[str, ...], str]] = [
    # where the user lives
    (r"where\s+do\s+i\s+(?:currently\s+)?live", ("city", "town"), "What"),
    (r"(?:what|which)\s+city\s+do\s+i\s+live\s+in", ("city",), "What"),
    (r"(?:what|which)\s+town\s+do\s+i\s+live\s+in", ("town",), "What"),
    (r"(?:what|which)\s+country\s+do\s+i\s+live\s+in", ("country",), "What"),
    # marriage
    (r"who\s+am\s+i\s+married\s+to", ("spouse", "wife", "husband"), "Who"),
    (r"who\s+is\s+married\s+to\s+me", ("spouse", "wife", "husband"), "Who"),
    # work
    (r"where\s+do\s+i\s+work", ("employer", "workplace", "company"), "Who"),
    (r"who\s+do\s+i\s+work\s+for", ("employer", "company"), "Who"),
    (r"(?:what|which)\s+company\s+do\s+i\s+work\s+(?:for|at)",
     ("employer", "company"), "Who"),
    (r"who\s+do\s+i\s+report\s+to", ("boss",), "Who"),
    (r"what\s+do\s+i\s+do\s+for\s+(?:a\s+)?(?:living|work)",
     ("job", "occupation", "profession"), "What"),
    (r"what\s+(?:job|work)\s+do\s+i\s+do", ("job", "occupation", "profession"),
     "What"),
    (r"what\s+do\s+i\s+work\s+as", ("job", "occupation", "profession"), "What"),
    # origin
    (r"where\s+was\s+i\s+born", ("birthplace",), "What"),
    (r"(?:what|which)\s+(?:city|town|place)\s+was\s+i\s+born\s+in",
     ("birthplace",), "What"),
    (r"where\s+did\s+i\s+grow\s+up", ("hometown",), "What"),
    (r"where\s+am\s+i\s+from", ("hometown", "country"), "What"),
    (r"(?:what|which)\s+country\s+am\s+i\s+from", ("country",), "What"),
    # other stored USER relations
    (r"how\s+old\s+am\s+i", ("age",), "What"),
    (r"what\s+pet\s+do\s+i\s+have", ("pet",), "What"),
    (r"(?:what|which)\s+school\s+do\s+i\s+(?:go\s+to|attend)", ("school",),
     "What"),
    (r"where\s+do\s+i\s+go\s+to\s+school", ("school",), "What"),
    (r"what\s+languages?\s+do\s+i\s+speak", ("language",), "What"),
]
_MAP_RE249 = [(re.compile(r"^" + _LEAD + body + _TAIL + r"\s*\?+$", re.I),
               rels, wh) for body, rels, wh in MAP249]

# "What's / Who's / Where's my <chain>?" (straight or curly apostrophe).
_WHATS_MY249 = re.compile(
    r"^" + _LEAD + r"(what|who|where)(?:'|’)s\s+my\s+(.+?)" + _TAIL
    + r"\s*\?+$", re.I)
_FIRST_PERSON249 = re.compile(r"\b(?:i|me|my)\b", re.I)


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def _user_index249(nb) -> dict[str, dict[str, list[str]]]:
    """lower(entity name) -> relation -> [values] over active taught facts."""
    out: dict[str, dict[str, list[str]]] = {}
    facts = getattr(nb, "facts", None)
    if not isinstance(facts, dict):
        return out
    for fact in facts.values():
        try:
            if fact.get("source") != "taught" or not nb.active(
                    fact["fact_id"]):
                continue
            subj = str(nb.entities.get(fact["subject"], "")).strip()
            val = str(L90._display(nb, fact["value"])).strip()
        except Exception:  # noqa: BLE001
            continue
        if subj and val:
            out.setdefault(subj.lower(), {}).setdefault(
                str(fact["relation"]), []).append(val)
    return out


def _chain_resolves249(idx, relations: list[str]) -> bool:
    frontier = [USER249.lower()]
    for rel in relations:
        nxt = []
        for ent in frontier:
            nxt.extend(v.lower() for v in idx.get(ent, {}).get(rel, []))
        if not nxt:
            return False
        frontier = nxt
    return True


def rewrite249(turn: str, nb) -> dict | None:
    """Question about the user -> {"text", "relations", "rule"} or None."""
    t = _norm(turn)
    if not t.endswith("?") or nb is None:
        return None
    if not _FIRST_PERSON249.search(t):
        return None
    m = _WHATS_MY249.match(t)
    if m is not None:
        chain = [p.strip() for p in re.split(A._APOS, m.group(2).strip())
                 if p.strip()]
        rels = [M166.canonical_relation(p) for p in chain]
        if not chain or any(r is None for r in rels):
            return None
        if not _chain_resolves249(_user_index249(nb), rels):  # type: ignore[arg-type]
            return None
        wh = m.group(1).capitalize()
        return {"text": f"{wh} is my {m.group(2).strip()}?",
                "relations": rels, "rule": "whats-my"}
    for rx, cands, wh in _MAP_RE249:
        if rx.match(t) is None:
            continue
        mine = _user_index249(nb).get(USER249.lower(), {})
        stored = [r for r in cands if mine.get(r)]
        if len(stored) != 1:
            return None  # none stored, or ambiguous: keep the original
        rel = stored[0]
        return {"text": f"{wh} is my {rel.replace('_', ' ')}?",
                "relations": [rel], "rule": rx.pattern}
    return None


def _is_me_ask249(actions, relations) -> bool:
    if not isinstance(actions, list) or len(actions) != 1:
        return False
    a = actions[0]
    return (isinstance(a, dict) and a.get("act") == "ask"
            and bool(a.get("me166")) and a.get("name") == USER249
            and list(a.get("relations") or []) == list(relations))


class FirstPerson249Mixin:
    """Outermost ears stage: first-person questions -> Me166 "my" forms."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        text = str(turn)
        if not text.rstrip().endswith("?"):
            return super().hear(turn)  # type: ignore[misc]
        rw = rewrite249(text, getattr(self, "nb", None))
        if rw is None:
            return super().hear(turn)  # type: ignore[misc]
        actions = super().hear(rw["text"])  # type: ignore[misc]
        if _is_me_ask249(actions, rw["relations"]):
            self.last249 = (text, rw["text"])
            try:
                self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                    STAGE249, 1.0)
            except AttributeError:
                pass
            return actions
        return super().hear(turn)  # type: ignore[misc]


class Render249Mixin:
    """Loop-level render for 249-claimed turns only: the said lines get the
    same Me166 rendering ("USER's city is X." -> "Your city is X.") that the
    loop already applies to "my" questions, keyed on the rewritten text.
    Every other turn passes through untouched."""

    def _listening_tick(self):  # type: ignore[no-untyped-def]
        ears = getattr(self, "_ears249", None)
        if ears is not None:
            ears.last249 = None
        event = super()._listening_tick()  # type: ignore[misc]
        last = getattr(ears, "last249", None) if ears is not None else None
        if not last:
            return event
        ears.last249 = None
        try:
            turn = event.get("detail", {}).get("turn", "")
            if turn != last[0]:
                return event
            event["said"] = [L166.rewrite_me166_reply(line, last[1])
                             for line in event.get("said", [])]
        except Exception:  # noqa: BLE001 -- never break the loop on render
            pass
        return event
