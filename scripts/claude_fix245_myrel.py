#!/usr/bin/env python3
"""Exp 245 -- THE ONE CHANGE: "my <relation>" as a question subject/possessor.

Problem (30-conversation panel, exp 239; diagnosis 243): questions such as
"What's my uncle's job?" reach an inner reader that treats "my uncle" as a
person's NAME ("I don't know anyone called my uncle."), and verb forms such
as "Where does my sister live?" get the glued decline, even when the user's
relative and the asked fact are stored.

Mixin MyRel245Mixin sits OUTERMOST on the 138i ears (above ChainOf174). It
acts only on turns that end in "?" and contain "my <word>". Order:

1. The base ears hear the turn unchanged. If the base already reads it as
   a question about the user (Me166 ask, name == USER) or as any ask whose
   name is not the garbled "my ..." name, the base actions are returned
   untouched (forms that already work stay byte-identical). Otherwise a
   leading greeting/"please" and a trailing ", please" are dropped (this
   path only) before steps 2-4.
2. <word> is looked up among the user's stored relations exactly as the
   notebook stores them: the word itself, or the key that the existing
   Me166 teach mapping (fable_fix166_me.canonical_relation) stored it
   under. No new synonym list.
3. Structure: the text is rewritten with the stored person X in place of
   "my <word>" and heard by the unchanged base. If that is not an ask about
   X, the same text with a stand-in one-word name is heard instead (so the
   base's verb/possessive readers can parse it even when X is two words or
   lowercase); the stand-in never reaches the notebook (its ask is re-aimed
   at X). No ask about the stand-in/X -> step 5.
4. For each stored X (in notebook order): notebook.ask(X, relations) (read
   only). Every X with an OK answer gets the base's own ask action about X,
   so the base answers and renders it ("Tavi's city is Brellmoor."). 2+ X:
   one answer per person, each naming its person (declared behaviour).
   No X answers -> clarify "I don't know your <relation>'s <asked> yet."
   (Me166's own decline wording; never names X).
   No relative stored -> clarify "I don't know who your <relation> is."
5. No structure found: the base actions are returned unchanged, except that
   an ask whose name is the garbled "my <word>" becomes the grammatical
   decline ("I don't know who your <word> is." when no such relative is
   stored, "I don't know that about your <word>." when one is).

Never writes: every returned action is "ask" or "clarify".
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix166_me as M166  # noqa: E402 (USER key + Me166 mapping, read-only)
import fable_notebook_contract as C  # noqa: E402 (status names, read-only)

STANDIN245 = "Qzvxor"  # stand-in one-word name for the parse probe only
_MY = re.compile(r"\bmy\s+([A-Za-z][A-Za-z\-]*)", re.IGNORECASE)
# Politeness around a my-relation question (used ONLY inside this mixin's
# own path, after the base has refused the raw turn): a leading greeting /
# "please" and a trailing ", please" are dropped before the probes.
_LEAD = re.compile(r"^(?:(?:hi|hello|hey)(?:\s+there)?|please|ok|okay)"
                   r"\s*[,!.]?\s+(?=\S)", re.IGNORECASE)
_TRAIL = re.compile(r"[,\s]+please\s*\?$", re.IGNORECASE)


def polite_strip(text: str) -> str:
    """"Hi, where does my sister live, please?" -> "Where does my sister live?"."""
    out = text
    for _ in range(3):
        new = _LEAD.sub("", out, count=1)
        if new == out:
            break
        out = new
    out = _TRAIL.sub("?", out)
    if out and out != text:
        out = out[0].upper() + out[1:]
    return out


def _norm(text: object) -> str:
    return " ".join(str(text).split())


def user_relatives(nb) -> dict[str, list[str]]:
    """{relation key: [display names of X, notebook order]} for USER facts."""
    out: dict[str, list[str]] = {}
    try:
        found = nb.resolve(M166.USER_KEY)
    except Exception:
        return out
    if found.status != C.OK:
        return out
    uid = found.detail["entity_id"]
    for fid, fact in nb.facts.items():
        if fact.get("subject") != uid or fact.get("source") != "taught":
            continue
        if not nb.active(fid):
            continue
        value = fact.get("value", {})
        if "entity" in value:
            name = nb.entities.get(value["entity"], "")
        else:
            name = str(value.get("literal", ""))
        if name:
            out.setdefault(fact["relation"], []).append(name)
    return out


def relation_key(word: str, stored: dict[str, list[str]]) -> str | None:
    """Question word -> the key the notebook stores for USER, else None."""
    low = word.lower()
    if low in stored:
        return low
    try:
        key = M166.canonical_relation(low)
    except Exception:
        key = None
    if key and key in stored:
        return key
    return None


def _asks(actions) -> list[dict]:
    return [a for a in (actions or []) if isinstance(a, dict)
            and a.get("act") == "ask"]


def _garbled(actions) -> dict | None:
    for a in _asks(actions):
        if str(a.get("name", "")).strip().lower().startswith("my "):
            return a
    return None


def _clarify(text: str) -> list[dict]:
    return [{"act": "clarify", "text": text, "stage": "loop245-myrel",
             "myrel245": True}]


class MyRel245Mixin:
    """Outermost ears mixin: "my <relation>" questions resolve via USER facts."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        text = _norm(turn)
        if not text.endswith("?"):
            return super().hear(turn)  # type: ignore[misc]
        matches = list(_MY.finditer(text))
        if not matches:
            return super().hear(turn)  # type: ignore[misc]
        base = super().hear(turn)  # type: ignore[misc]
        garbled = _garbled(base)
        if _asks(base) and garbled is None:
            return base  # base already reads it (Me166 or another reader)
        nb = getattr(self, "nb", None)
        if nb is None:
            return base
        work = polite_strip(text)
        wmatches = list(_MY.finditer(work))
        try:
            plan = self._plan245(work, wmatches, nb) if wmatches else None
        except Exception:
            plan = None
        if plan is not None:
            self.last_stage, self.last_score = "loop245-myrel", 1.0  # type: ignore[attr-defined]
            return plan
        if garbled is not None:
            word = str(garbled.get("name", "")).strip().split(None, 1)[-1]
            stored = user_relatives(nb)
            if relation_key(word, stored) is None:
                return _clarify(f"I don't know who your {word.lower()} is.")
            return _clarify(f"I don't know that about your {word.lower()}.")
        return base

    # ------------------------------------------------------------ helpers
    def _probe245(self, text: str, target: str) -> dict | None:
        try:
            acts = super().hear(text)  # type: ignore[misc]
        except Exception:
            return None
        asks = _asks(acts)
        if len(asks) != 1 or len(acts) != 1:
            return None
        ask = asks[0]
        if _norm(ask.get("name", "")).lower() != _norm(target).lower():
            return None
        if not ask.get("relations"):
            return None
        return ask

    def _plan245(self, text: str, matches, nb) -> list[dict] | None:
        stored = user_relatives(nb)
        chosen = None
        for m in matches:
            key = relation_key(m.group(1), stored)
            if key is not None:
                chosen = (m, key)
                break
        if chosen is None:
            # No such relative stored: decline only when the question is
            # really about "my <word>" as subject/possessor.
            m = matches[0]
            cand = text[:m.start()] + STANDIN245 + text[m.end():]
            if self._probe245(cand, STANDIN245) is None:
                return None
            return _clarify(f"I don't know who your {m.group(1).lower()} is.")
        m, key = chosen
        people = stored[key]
        rels = None
        per_person: list[tuple[str, dict]] = []
        for x in people:
            cand = text[:m.start()] + x + text[m.end():]
            ask = self._probe245(cand, x)
            if ask is not None:
                per_person.append((x, dict(ask)))
                rels = list(ask["relations"])
        if rels is None:
            cand = text[:m.start()] + STANDIN245 + text[m.end():]
            ask = self._probe245(cand, STANDIN245)
            if ask is None:
                return None
            rels = list(ask["relations"])
        by_x = dict(per_person)
        out: list[dict] = []
        for x in people:
            act = by_x.get(x)
            if act is None:
                act = {"act": "ask", "name": x, "relations": list(rels),
                       "stage": "fake"}
            try:
                res = nb.ask(act["name"], list(act["relations"]))
            except Exception:
                continue
            if res.status == C.OK:
                act["myrel245"] = True
                out.append(act)
        if out:
            return out
        chain = M166.chain_display([key] + rels)
        return _clarify(f"I don't know your {chain} yet.")
