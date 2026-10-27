#!/usr/bin/env python3
"""Experiment 164 -- THE ONE CHANGE: a read-only about-stage before the fallback.

Director probe 04:12 on loop138/138c: after "Tom's boss is Ann." the question
"What do you know about Tom?" (and bare "What do you know?") falls through to
the fallback clarify ("I do not know that from what you taught me..." /
"I didn't understand that..."), even though the notebook holds the fact.
Users ask this constantly; it is the cheapest way to show what the notebook
holds.

THE RULE (a read-only ears stage, checked FIRST in hear(), before the base
loop150 chain and therefore before the fallback clarify at
scripts/fable_loop90_agent.py:291-292):

  Full-turn match only (case-insensitive, collapsed whitespace, optional
  trailing ".", "?" or "!"):
    P0  "What do you know?"                       -> notebook summary
    P1  "What do you know about X?"               -> facts about X
    P2  "Tell me about X"                         -> facts about X
    P3  "What have I told you about X?"           -> facts about X
    P4  "Anything about X?"                       -> facts about X

  X must be a plain name span: non-empty, starts alnum, charset
  [A-Za-z0-9 \\-'] only, no "'s"/"'s" (possessive chains delegate, e.g.
  "Tom's boss"), no whole-word "and"/"or" (compounds delegate), and not a
  pronoun below (reflexives + "Tell me about yourself" delegate to the exact
  base fallback).

  Resolution and reads use the notebook contract only (never the web, never
  inference):
    - nb.resolve(X): UNKNOWN_ENTITY -> the base's EXISTING unknown-entity
      reply (scripts/fable_notebook_contract.py:81,
      "I don't know anyone called {name}.", reused verbatim, never invented).
      AMBIGUOUS -> delegate to the base chain (byte-identical behaviour).
    - OK -> every ACTIVE taught fact (nb.active, same filter as
      scripts/fable_loop90_agent.py:101 notebook_triples) with X as subject
      (fact_id order) then every such fact with X as value (fact_id order),
      each rendered "Tom's boss is Ann." (relation underscores -> spaces).
      Max 8 sentences, then "and N more.". Retracted/superseded facts never
      appear (nb.active is False for them); non-taught sources never appear.
    - OK but zero active taught facts -> delegate to the base chain
      (byte-identical; no new strings invented for this edge).
    - P0 summary from the notebook: "I have N facts about M people. Ask me
      about one of them, like 'What do you know about Tom?'" with N = active
      taught facts and M = distinct subject entities.

  The stage returns a clarify action (mouth renders the text verbatim), so an
  about-turn NEVER writes: no notebook append, no web, no inference. Any
  internal error delegates to the base chain (never breaks the loop).

No existing file is edited; loop164 stacks this mixin onto loop150.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (resolve/active/template, read-only)

# Sealed pronoun exclusion: about-turns over these delegate to the exact base
# fallback (they are not stored person names). One-line reasons each:
# reflexives are never entity names; me/you/him/her/it/us/them are pronouns,
# never taught as person names (teaches put names in subject position).
PRONOUN_EXCLUDE = frozenset({
    "myself", "yourself", "himself", "herself", "itself",
    "ourselves", "yourselves", "themselves",
    "me", "you", "him", "her", "it", "us", "them",
})

_P0 = re.compile(r"^\s*what\s+do\s+you\s+know\s*[?.!]?\s*$", re.IGNORECASE)
_P1 = re.compile(r"^\s*what\s+do\s+you\s+know\s+about\s+(.+?)\s*[?.!]?\s*$",
                 re.IGNORECASE | re.DOTALL)
_P2 = re.compile(r"^\s*tell\s+me\s+about\s+(.+?)\s*[?.!]?\s*$",
                 re.IGNORECASE | re.DOTALL)
_P3 = re.compile(r"^\s*what\s+have\s+i\s+told\s+you\s+about\s+(.+?)\s*[?.!]?\s*$",
                 re.IGNORECASE | re.DOTALL)
_P4 = re.compile(r"^\s*anything\s+about\s+(.+?)\s*[?.!]?\s*$",
                 re.IGNORECASE | re.DOTALL)

_X_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-'’]*$")
_AND_OR = re.compile(r"\b(and|or)\b", re.IGNORECASE)

MAX_FACTS = 8


def _clean_tail(raw: str) -> str:
    """Collapse whitespace, drop ONE trailing run of . ? ! (punct variants)."""
    text = " ".join(str(raw).split())
    return text.rstrip("?.!")


def _valid_x(raw: str) -> str | None:
    """Tail -> clean X, or None when the turn must delegate to the base."""
    x = _clean_tail(raw)
    if not x:
        return None
    low = x.lower()
    if low in PRONOUN_EXCLUDE:
        return None
    if "'s" in low or "’s" in low:
        return None  # possessive chain ("Tom's boss"): base router's job
    if _AND_OR.search(x):
        return None  # compound ("Tom and Ann"): base fallback's job
    if not _X_OK.match(x):
        return None  # punctuation/frames the stage never claims
    return x


def match_about(turn: str) -> tuple | None:
    """Full-turn about-shape -> ("summary",) | ("about", X) | None (delegate).

    Pure function of the turn text (no notebook, no writes). Returns None for
    every turn the stage must not claim, including all teaches.
    """
    text = " ".join(str(turn).split())
    if not text:
        return None
    if _P0.match(text):
        return ("summary",)
    for rx in (_P1, _P2, _P3, _P4):
        m = rx.match(text)
        if m:
            x = _valid_x(m.group(1))
            return ("about", x) if x is not None else None
    return None


def _display(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], value["entity"])
    return str(value.get("literal", ""))


def _norm_lit(text: str) -> str:
    return " ".join(str(text).split()).lower()


def fact_sentences(nb, entity_id: str | None, x_norm: str) -> list[str]:
    """Active taught facts: X-as-subject (fact_id order), then X-as-value.

    Value side covers both entity values (``nb.resolve`` hit) and literal
    values whose normalised text equals X (literals mint no entity, e.g.
    Paris in "Tom's city is Paris."). ``entity_id`` is None when X resolves
    UNKNOWN_ENTITY: only the literal side can match then.
    """
    subj, val = [], []
    for fid, fact in nb.facts.items():
        if fact.get("source") != "taught" or not nb.active(fid):
            continue
        s = f"{nb.entities.get(fact['subject'], '?')}'s " \
            f"{str(fact['relation']).replace('_', ' ')} is " \
            f"{_display(nb, fact['value'])}."
        if entity_id is not None and fact.get("subject") == entity_id:
            subj.append(s)
        elif isinstance(fact.get("value"), dict):
            if entity_id is not None \
                    and fact["value"].get("entity") == entity_id:
                val.append(s)
            elif "literal" in fact["value"] and _norm_lit(
                    fact["value"]["literal"]) == x_norm:
                val.append(s)
    return subj + val


def about_reply(nb, entity_id: str | None, x_norm: str) -> str:
    """Known/literal-X reply: up to MAX_FACTS sentences, then "and N more."."""
    sents = fact_sentences(nb, entity_id, x_norm)
    if len(sents) <= MAX_FACTS:
        return " ".join(sents)
    head = sents[:MAX_FACTS]
    return " ".join(head) + f" and {len(sents) - MAX_FACTS} more."


def summary_reply(nb) -> str:
    """P0 reply: counts from the notebook only (active taught facts)."""
    n, subjects = 0, set()
    for fid, fact in nb.facts.items():
        if fact.get("source") != "taught" or not nb.active(fid):
            continue
        n += 1
        subjects.add(fact["subject"])
    return (f"I have {n} facts about {len(subjects)} people. Ask me about "
            f"one of them, like 'What do you know about Tom?'")


def unknown_reply(name: str) -> str:
    """The base's EXISTING unknown-entity reply (contract template, reused)."""
    return C.Result(C.UNKNOWN_ENTITY, {"name": name}).say()


class About164Mixin:
    """Stackable read-only about-stage: hear() checks about-shapes FIRST.

    Cooperative (super() last): anything the stage does not claim, cannot
    resolve, or fails on delegates byte-identical to the base chain. The
    stage only ever returns clarify actions: 0 writes on every about-turn.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        try:
            nb = getattr(self, "nb", None)
            if nb is not None:
                parsed = match_about(turn)
                if parsed is not None and parsed[0] == "summary":
                    return [{"act": "clarify", "text": summary_reply(nb)}]
                if parsed is not None and parsed[0] == "about":
                    found = nb.resolve(parsed[1])
                    x_norm = _norm_lit(parsed[1])
                    if found.status == C.OK:
                        eid = found.detail["entity_id"]
                        if fact_sentences(nb, eid, x_norm):
                            return [{"act": "clarify",
                                     "text": about_reply(nb, eid, x_norm)}]
                        # Known name, zero facts: delegate (no new strings).
                    elif found.status == C.UNKNOWN_ENTITY:
                        if fact_sentences(nb, None, x_norm):
                            return [{"act": "clarify",
                                     "text": about_reply(nb, None, x_norm)}]
                        return [{"act": "clarify",
                                 "text": unknown_reply(parsed[1])}]
                    # AMBIGUOUS -> delegate (base behaviour, byte-identical).
        except Exception:
            pass  # never break the loop: fall through to the base chain
        return super().hear(turn)  # type: ignore[misc]
