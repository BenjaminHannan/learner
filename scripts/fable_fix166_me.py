#!/usr/bin/env python3
"""Experiment 166 -- THE ONE CHANGE: first-person ("my") teaches/asks map to a
reserved notebook entity for the user.

Ben's ruling (2026-09-22): "me"/"my"/"I" is the user, and there is exactly one
user. A single reserved notebook entity (internal key USER_KEY = "USER", fixed
in this doc, never shown raw in any reply) owns every first-person possessive
fact:

    "My mom is Rita."      -> stores (USER, mother, Rita),
                              reply "Saved: your mother is Rita."
    "Who is my mom?"       -> "Your mother is Rita."
    "Where is my mom's city?" (with (Rita, city, Lisbon) taught) hops the
                              normal path -> "Your mother's city is Lisbon."
    unknown                -> "I don't know your mother yet."

Second-person turns about the agent ("What is your name?", "Who made you?")
and everything else take the loop162b code path literally (byte-identical by
construction: the mixin below only claims turns whose subject/head is the
first-person possessive "my", which loop162b always refuses -- see Step 1 in
design doc 166).

No existing file is edited. Base modules are imported read-only. Reply
rendering (USER -> your/Your) lives in scripts/fable_loop166_agent.py
(Loop166AgentLoop._listening_tick post-pass, gated on this file's parser).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (FakeEars shapes, read-only)
import fable_fix135_office as F135  # noqa: E402 (office family, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject screen, read-only)
import fable_fix162_thename as T162  # noqa: E402 (norm/correction lead, read-only)
import fable_loop102_agent as L102  # noqa: E402 (hearsay + qualifier, read-only)
import fable_loop121_agent as L121  # noqa: E402 (value screen, read-only)
import fable_loop90_agent as L90  # noqa: E402 (Bench73Stage, read-only)

# The one reserved key. Stored as the entity display name in the notebook;
# replies are rewritten before they reach the user (loop166 agent), so this
# raw form never appears in any reply.
USER_KEY = "USER"

# First-person possessive head. Only "my" (the possessive); "your" (agent),
# bare nouns, and "The X" shapes never match here.
_MY_HEAD = re.compile(r"^my\b\s*(.*)$", re.IGNORECASE | re.DOTALL)

# Teach frame (strict full-turn): "My <R> is <V>." -- single relation only,
# like the base ("Tom's mother's city is X" is a base clarify, and stays one).
_TEACH = re.compile(r"^my\s+(.+?)\s+is\s+(.+?)\s*$",
                    re.IGNORECASE | re.DOTALL)

# Ask frame: "Who/What/Where is|are my <chain>?" where chain is
# possessive-linked ("mom", "mom's city", "father's friend's city").
_ASK = re.compile(r"^(who|what|where)\s+(is|are)\s+my\s+(.+?)\s*\??\s*$",
                  re.IGNORECASE | re.DOTALL)

# Relation surface shape: same letters/spaces/slash/hyphen rule as exp 162.
_REL_SHAPE = re.compile(r"[A-Za-z][A-Za-z /-]*")

# First-person relation synonyms -> canonical loop relation keys.
# Canonical keys are the loop's own (FakeEars identity normalisation +
# person/table keys); office heads are vetoed separately below.
_SYNONYMS = {
    "mom": "mother", "mum": "mother", "mommy": "mother", "mummy": "mother",
    "ma": "mother",
    "dad": "father", "daddy": "father", "papa": "father", "pop": "father",
    "poppa": "father", "pa": "father",
}


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def canonical_relation(surface: str) -> str | None:
    """First-person relation surface -> canonical loop key, or None.

    None (fall through to the base path byte-identical) when the surface has
    the wrong shape or is an exp-135 office head (president/mayor/boss-class
    stays on the base path exactly). Anything else the base FakeEars shape
    would store for a one-word name is storable for USER too, so the normal
    hop path works over it (city included).
    """
    text = _norm(surface)
    if not _REL_SHAPE.fullmatch(text):
        return None
    lowered = text.lower()
    if " " in lowered.strip():
        # Multi-word relations ("best friend") stay on the base path: the
        # base joins them with "_" and the me frames stay single-word, so a
        # taught fact is always askable in the same words.
        return None
    if F135.is_office_head(lowered):
        return None
    key = _SYNONYMS.get(lowered, "_".join(lowered.split()))
    if not key:
        return None
    return key


def _split_chain(inner: str) -> list[str] | None:
    """"mom's city" -> ["mom", "city"]; bare "mom" -> ["mom"]."""
    parts = [p.strip() for p in re.split(A._APOS, inner.strip())
             if p.strip()]
    if not parts:
        return None
    return parts


def parse_me_teach(turn: str) -> dict | None:
    """Raw turn -> {key, Rsurf, V} for "My <R> is <V>." or None."""
    text = _norm(turn)
    if not text or text.rstrip().endswith("?"):
        return None
    body = text
    if body.endswith(".") and not body.endswith(".."):
        body = body[:-1].strip()
    if not body:
        return None
    body = L102.strip_trailing_qualifier(body)
    m = T162._CORRECTION_LEAD.match(body)
    if m and m.group(2).strip():
        body = m.group(2).strip()
    m = _TEACH.fullmatch(body)
    if m is None:
        return None
    rsurf, val = m.group(1).strip(), m.group(2).strip()
    if not rsurf or not val:
        return None
    if "?" in val or ";" in val:
        return None
    # Chained teaches ("My mom's city is X") stay on the base path, exactly
    # like the base's chained teaches.
    if re.search(A._APOS, rsurf):
        return None
    key = canonical_relation(rsurf)
    if key is None:
        return None
    return {"key": key, "Rsurf": _norm(rsurf), "V": val}


def parse_me_ask(turn: str) -> dict | None:
    """Raw turn -> {relations} for "Who/What/Where is|are my <chain>?" or None.

    Only claims the turn when EVERY link maps to a storable canonical key
    (office heads and bad shapes fall through to the base path untouched).
    """
    text = _norm(turn)
    if not text:
        return None
    m = _ASK.fullmatch(text)
    if m is None:
        return None
    chain = _split_chain(m.group(3))
    if not chain:
        return None
    relations = []
    for link in chain:
        key = canonical_relation(link)
        if key is None:
            return None
        relations.append(key)
    if not relations or len(relations) > A.MAX_HOPS:
        return None
    return {"relations": relations}


def chain_display(relations: list[str]) -> str:
    """["mother", "city"] -> "mother's city" (surface words for replies)."""
    words = [r.replace("_", " ") for r in relations]
    return "'s ".join(words)


class Me166Mixin:
    """Stackable mixin: first-person frames before the loop162b stages.

    Cooperative: the "my" teach/ask frames are matched BEFORE the base hear
    (loop162b refuses every such turn -- Step 1 in doc 166); anything this
    frame declines -- every second-person turn, every bare/third-person turn,
    office heads, chained teaches -- falls through to super().hear()
    untouched, so non-first-person behaviour is the loop162b code literally.
    Same screens/save as 162/162b (121 value, 102 hearsay/qualifier, 150
    subject, Bench73Stage._teach_action with is_person=True so values stay
    entity-valued and mid-chain hops work); the loop _act guards still apply.
    Asks go through the normal hop path with name=USER_KEY.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        # ---- teach side: "My <R> is <V>." ----
        parsed = parse_me_teach(turn)
        if parsed is not None and nb is not None:
            if not L102.subject_is_hearsay_shaped(USER_KEY):
                if L121.screen_value_121(parsed["V"]) is None:
                    verdict, payload = S150.screen_subject_150(USER_KEY)
                    if verdict == "store":
                        stage = L90.Bench73Stage()
                        stage.bind(nb)
                        action = stage._teach_action(
                            (payload, parsed["key"], parsed["V"]))
                        action["is_person"] = True
                        action["stage"] = "loop166"
                        action["me166"] = True
                        self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                            "loop166-me", 1.0)
                        return [action]
            return super().hear(turn)  # type: ignore[misc]
        # ---- ask side: "Who/What/Where is|are my <chain>?" ----
        qparsed = parse_me_ask(turn)
        if qparsed is not None and nb is not None:
            action = {"act": "ask", "name": USER_KEY,
                      "relations": list(qparsed["relations"]),
                      "stage": "fake", "me166": True}
            self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                "loop166-me", 1.0)
            return [action]
        return super().hear(turn)  # type: ignore[misc]
