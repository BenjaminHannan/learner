#!/usr/bin/env python3
"""Experiment 293 -- THE ONE CHANGE: a yes/no reader on 138nb (additive).

Diagnosis (artifacts/claude-diag293-20260923/DIAG.md, read-only): on 138nb,
40 of 51 yes/no turns get "I didn't understand that question" -- 16 where
the fact IS stored, 24 where nothing is stored. The base parser only turns
who/what/where into questions (scripts/fable_agent_loop.py:96); the only
live yes/no reader is 154d (scripts/fable_fix154d_yesno.py, imported
READ-ONLY below), which reads only "Is X's R V?" / "Is V X's R?" with
one-word capitalised names and exactly one "'s".

THE ONE CHANGE (design/v3/30-modes/293-yesno-questions.md): 293 = 138nb +
one yes/no reader in the 154d slot (this new wrapper file; 154d's code is
imported read-only, never copied). It parses:
  "Does A have a/an R?", "Has A got a/an R?" (also article-free "Does A
  have R?" / "Has A a R?");
  "Does A live in V?" (key city), "Does A work at/for V?" (key employer),
  "Does A come from V?" / "Was A born in V?" (key birthplace);
  the "Is" shapes, now with multi-word names (resolved against names the
  notebook holds) and of-forms ("Is V the R of A?").
It answers read-only from the notebook:
  Yes: the stored value matches ("Yes, Ana's dentist is Tovi.");
  No: only for single-valued relations (SINGLE_VALUED_293 below), when a
      different value is stored ("No, Ana's city is Oslo.");
  "I don't know": nothing is stored for that relation, or the relation is
      multi-valued and V is not among its values (the reply names what is
      stored); never writes; a taken-back value counts as not stored.
Chain subjects ("Does Ana's boss live in Oslo?") stay out: they pass
through unchanged (any "'s" inside the subject, or an unresolvable
subject span, returns None and the base reply is kept byte-identical).

Firing rule (same gate as 154d): only when the unchanged forward path
returns exactly the didn't-understand clarify for the turn. All other
turns (wh-answers, targeted declines, no-save clarifies, statements
without "?", or-/and-questions, lowercase subjects) delegate
byte-identical to super(). The stage never writes: it only calls
nb.resolve / nb.current (reads), and the final record is a clarify the
mouth renders verbatim.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (LISTENING mode, read-only)
import fable_fix154d_yesno as D154  # noqa: E402 (154d reader, read-only)
import fable_notebook_contract as C  # noqa: E402 (OK status, read-only)
from fable_fix154_yesno import SINGLE_VALUED_154  # noqa: E402 (code table)

# 154d's single-valued slots, plus the work/born/dentist/coach/doctor keys
# this reader verifies. Multi-valued relations (sister, brother, friend,
# dog, ...) never license "No": a mismatch there is "Not that I know of".
SINGLE_VALUED_293 = frozenset(
    set(SINGLE_VALUED_154)
    | {"employer", "birthplace", "dentist", "doctor", "coach"}
)

# The forward path's total-miss reply (same text 154d keys on).
DIDNT_UNDERSTAND_293 = D154.DIDNT_UNDERSTAND_154D

# "place of birth" / "birth place" surfaces teach under key "birthplace"
# ("A's birthplace is P."); unify the keys so all surfaces verify.
_KEY_ALIAS_293 = {"place_of_birth": "birthplace",
                  "birth_place": "birthplace"}

_DOES_HAVE_293 = re.compile(r"^\s*Does\s+(.+?)\s+have\s+(.+?)\s*\?+\s*$")
_HAS_293 = re.compile(r"^\s*Has\s+(.+?)\s*\?+\s*$")
_DOES_LIVE_293 = re.compile(r"^\s*Does\s+(.+?)\s+live\s+in\s+(.+?)\s*\?+\s*$")
_DOES_WORK_293 = re.compile(
    r"^\s*Does\s+(.+?)\s+work\s+(?:at|for)\s+(.+?)\s*\?+\s*$")
_DOES_FROM_293 = re.compile(
    r"^\s*Does\s+(.+?)\s+come\s+from\s+(.+?)\s*\?+\s*$")
_WAS_BORN_293 = re.compile(
    r"^\s*Was\s+(.+?)\s+born\s+in\s+(.+?)\s*\?+\s*$")
_IS_293 = re.compile(r"^\s*Is\s+(.+?)\s*\?+\s*$")
_OF_293 = re.compile(r"^(.+?)\s+[Tt]he\s+(.+?)\s+[Oo]f\s+(.+?)$")
_POSS_293 = re.compile(r"['\u2019]s\b")
_ORAND_293 = re.compile(r"(?i)\b(or|and)\b")
_ART_293 = re.compile(r"^(?:a|an|the)\s+(.+?)$")


def _collapse(text: str) -> str:
    return " ".join(str(text).split())


def relation_key293(surface: str) -> str:
    """The loop's own relation mapping (FakeEars._relation, read-only)."""
    key = A.FakeEars._relation(surface)
    return _KEY_ALIAS_293.get(key, key)


def _resolve_eid(nb, name: str):
    """Entity id for a taught subject, or None (unknown/ambiguous)."""
    try:
        resolved = nb.resolve(name)
    except Exception:
        return None
    if resolved is None or getattr(resolved, "status", None) != C.OK:
        return None
    try:
        return (resolved.detail or {}).get("entity_id")
    except Exception:
        return None


def _rows(nb, eid, key: str) -> list:
    try:
        return list(nb.current(eid, key) or [])
    except Exception:
        return []


def _strip_article(span: str) -> str:
    m = _ART_293.match(span.strip())
    return m.group(1).strip() if m else span.strip()


def _subject_ok(name: str) -> bool:
    """Subjects must be plain names: no chains, capitalised (154d rule)."""
    if not name or _POSS_293.search(name):
        return False
    return name[:1].isupper()


def _parse_has(body: str):
    """Split a Has-body into [(owner-name, relation surface)] candidates.

    "got" anchors the split; otherwise the relation is the last 1-2
    tokens (minus an article) and the owner is the rest. Grounding tries
    each candidate's owner against the notebook in order.
    """
    toks = body.split()
    if not toks:
        return None
    low = [t.lower() for t in toks]
    if "got" in low:
        i = low.index("got")
        owner, rel = " ".join(toks[:i]), _strip_article(" ".join(toks[i + 1:]))
        if owner and rel:
            return [(owner, rel)]
        return None
    cands = []
    for nrel in (1, 2):
        if len(toks) > nrel:
            rel = _strip_article(" ".join(toks[-nrel:]))
            owner = " ".join(toks[:-nrel])
            if owner and rel:
                cands.append((owner, rel))
    return cands or None


def parse_yesno293(turn: str) -> dict | None:
    """Parse a yes/no turn -> {x, key, rel, v, owner} | None.

    v is None for existence ("have") questions. rel is the display
    relation word used in replies. None = pass through unchanged.
    """
    text = _collapse(turn)
    if not text.endswith("?") or _ORAND_293.search(text):
        return None
    m = _DOES_LIVE_293.match(text)
    if m:
        x, v = m.group(1).strip(), m.group(2).strip()
        if _subject_ok(x) and v:
            return {"x": x, "key": "city", "rel": "city", "v": v,
                    "owner": f"{x}'s city"}
        return None
    m = _DOES_WORK_293.match(text)
    if m:
        x, v = m.group(1).strip(), m.group(2).strip()
        if _subject_ok(x) and v:
            return {"x": x, "key": "employer", "rel": "employer",
                    "v": v, "owner": f"{x}'s employer"}
        return None
    m = _DOES_FROM_293.match(text)
    if m:
        x, v = m.group(1).strip(), m.group(2).strip()
        if _subject_ok(x) and v:
            return {"x": x, "key": "birthplace", "rel": "birthplace",
                    "v": v, "owner": f"{x}'s birthplace"}
        return None
    m = _WAS_BORN_293.match(text)
    if m:
        x, v = m.group(1).strip(), m.group(2).strip()
        if _subject_ok(x) and v:
            return {"x": x, "key": "birthplace", "rel": "birthplace",
                    "v": v, "owner": f"{x}'s birthplace"}
        return None
    m = _DOES_HAVE_293.match(text)
    if m:
        x, rel = m.group(1).strip(), _strip_article(m.group(2))
        key = relation_key293(rel) if rel else ""
        if _subject_ok(x) and rel and key:
            return {"x": x, "key": key, "rel": rel, "v": None,
                    "owner": f"{x}'s {rel}"}
        return None
    m = _HAS_293.match(text)
    if m:
        cands = _parse_has(m.group(1).strip())
        if not cands:
            return None
        return {"has_cands": cands, "case": "has"}
    m = _IS_293.match(text)
    if m:
        return _parse_is293(m.group(1).strip())
    return None


def _parse_is293(body: str) -> dict | None:
    """The Is family: of-forms plus possessive/inverted, multi-word names.

    Returns raw left/right token spans; ground_yesno293 tries the
    possessive reading first (whole left side is the owner) and falls
    back to the inverted reading (owner = longest taught-name suffix).
    """
    if not body:
        return None
    if re.match(r"(?i)^it\s", body):
        return None  # "Is it true that ...?" stays out (not a fact check)
    m = _OF_293.match(body)
    if m:
        v, rel, x = (m.group(1).strip(), m.group(2).strip(),
                     m.group(3).strip())
        key = relation_key293(rel) if rel else ""
        if _subject_ok(x) and v and rel and key:
            return {"x": x, "key": key, "rel": rel, "v": v,
                    "owner": f"{x}'s {rel}", "case": "of"}
        return None
    parts = _POSS_293.split(body)
    if len(parts) != 2:  # exactly one "'s": no two-hop, no bare "Is V?"
        return None
    left, right = parts[0].strip(), parts[1].strip()
    if not left or not right:
        return None
    return {"left": left.split(), "right": right.split(), "case": "is"}


def _split_rel_value(nb, eid: str, toks: list[str]) -> tuple | None:
    """Split possessive tail tokens into (key, rel-surface, value) | None.

    Longest grounded relation prefix wins; ungrounded falls back to a
    one-word relation so the reply can still name it honestly.
    """
    for i in range(min(len(toks) - 1, 4), 0, -1):
        rel = " ".join(toks[:i])
        key = relation_key293(rel)
        if key and _rows(nb, eid, key):
            return key, rel, " ".join(toks[i:])
    if len(toks) >= 2:
        rel = toks[0]
        key = relation_key293(rel)
        if key:
            return key, rel, " ".join(toks[1:])
    return None


def _owner_status(nb, x: str) -> str:
    """OK / AMBIGUOUS / other for a subject span (read-only)."""
    try:
        resolved = nb.resolve(x)
    except Exception:
        return "ERROR"
    return getattr(resolved, "status", "ERROR")


def _ground_is(nb, left: list[str], right: list[str]) -> str | None:
    """Possessive reading first, inverted fallback (read-only)."""
    xa = " ".join(left)
    if _subject_ok(xa):
        eid = _resolve_eid(nb, xa)
        if eid is not None and len(right) >= 2:
            split = _split_rel_value(nb, eid, right)
            if split is None:
                return None  # degenerate tail: base reply unchanged
            key, rel, v = split
            rows = _rows(nb, eid, key)
            if not rows:
                return f"I don't know {xa}'s {rel}."
            return _verdict(nb, rows, key, rel, v, f"{xa}'s {rel}")
        if eid is None and _owner_status(nb, xa) == C.AMBIGUOUS:
            return None  # ambiguous owner: base reply unchanged
    # Inverted reading ("Is V X's R?"): longest taught-name owner suffix.
    rel_b = " ".join(right)
    key_b = relation_key293(rel_b)
    if key_b and len(left) >= 2 and _subject_ok(left[-1]):
        for j in range(len(left) - 1, 0, -1):
            x = " ".join(left[j:])
            eid = _resolve_eid(nb, x)
            if eid is None:
                continue
            v = " ".join(left[:j])
            rows = _rows(nb, eid, key_b)
            if rows:
                return _verdict(nb, rows, key_b, rel_b, v,
                                f"{x}'s {rel_b}")
            return f"I don't know {x}'s {rel_b}."
        x = left[-1]
        if _resolve_eid(nb, x) is None:
            return f"I don't know anyone called {x}."
        return f"I don't know {x}'s {rel_b}."
    if _subject_ok(xa):
        return f"I don't know anyone called {xa}."
    return None


def ground_yesno293(nb, parsed: dict) -> str | None:
    """Notebook lookup for a parsed frame -> reply text | None (no write).

    None = pass through unchanged (chain subject or ambiguous owner).
    """
    case = parsed.get("case")
    if case == "is":
        return _ground_is(nb, parsed["left"], parsed["right"])
    if case == "has":
        last_owner = None
        for x, rel in parsed["has_cands"]:
            if not _subject_ok(x):
                continue
            last_owner = x
            key = relation_key293(rel)
            if not key:
                continue
            eid = _resolve_eid(nb, x)
            if eid is None:
                continue
            rows = _rows(nb, eid, key)
            if not rows:
                return f"I don't know {x}'s {rel}."
            shown = D154.join_and154d(
                [D154.show_value154d(nb, r.get("value")) for r in rows])
            return f"Yes, {x}'s {rel} is {shown}."
        if last_owner is not None:
            if _owner_status(nb, last_owner) == C.AMBIGUOUS:
                return None
            return f"I don't know anyone called {last_owner}."
        return None
    x = parsed["x"]
    eid = _resolve_eid(nb, x)
    if eid is None:
        if _owner_status(nb, x) == C.AMBIGUOUS:
            return None  # ambiguous owner: base reply unchanged
        return f"I don't know anyone called {x}."
    rows = _rows(nb, eid, parsed["key"])
    if not rows:
        return f"I don't know {parsed['owner']}."
    if parsed["v"] is None:  # existence ("have") question
        shown = D154.join_and154d(
            [D154.show_value154d(nb, r.get("value")) for r in rows])
        return f"Yes, {parsed['owner']} is {shown}."
    return _verdict(nb, rows, parsed["key"], parsed["rel"], parsed["v"],
                    parsed["owner"])


def _verdict(nb, rows: list, key: str, rel: str, v: str,
             owner: str) -> str:
    displays = [D154.show_value154d(nb, r.get("value")) for r in rows]
    want = D154.norm_value154d(v)
    if any(D154.norm_value154d(d) == want for d in displays):
        return f"Yes, {owner} is {_collapse(v)}."
    shown = D154.join_and154d(displays)
    if key in SINGLE_VALUED_293:
        return f"No, {owner} is {shown}."
    return f"Not that I know of. I have {shown} as {owner}."


def is_miss293(actions) -> bool:
    """True iff the forward path did not understand (154d's gate)."""
    return D154.is_miss154d(actions)


class YesNo293Mixin:
    """Stackable loop-level mixin: the 293 yes/no reader in the 154d slot.

    Cooperative (super() first on every other turn): _listening_tick peeks
    at the inbox head through the unchanged ears hear; non-miss turns
    delegate byte-identical to super(). On the miss clarify it tries
    154d's own parse+ground first (imported read-only: byte-identical
    replies and stage tags on everything 154d answers today), then the
    wider 293 parse+ground above. Grounded frames answer from notebook
    reads only (resolve + current); the final record is a clarify
    rendered verbatim by the mouth. Counters, last_records, experience
    and the event shape match the parent exactly. This path provably
    never writes.
    """

    def _listening_tick(self):  # type: ignore[no-redef]
        text = self.inbox[0] if getattr(self, "inbox", None) else None
        if text is not None:
            try:
                base = self.ears.hear(text)  # type: ignore[attr-defined]
            except Exception:
                base = None
            if base is not None and is_miss293(base):
                parsed154 = D154.parse_yesno154d(text)
                if parsed154 is not None:
                    try:
                        reply = D154.ground_yesno154d(
                            self.nb, parsed154)  # type: ignore[attr-defined]
                    except Exception:  # noqa: BLE001 -- never raise
                        reply = None
                    if reply is not None:
                        return self._answer_yesno293(
                            text, reply, "loop154d-yesno")
                parsed = parse_yesno293(text)
                if parsed is not None:
                    try:
                        reply = ground_yesno293(
                            self.nb, parsed)  # type: ignore[attr-defined]
                    except Exception:  # noqa: BLE001 -- never raise
                        reply = None
                    if reply is not None:
                        return self._answer_yesno293(
                            text, reply, "loop293-yesno")
        return super()._listening_tick()  # type: ignore[misc]

    def _answer_yesno293(self, text: str, reply: str, tag: str) -> dict:
        self.inbox.pop(0)  # type: ignore[attr-defined]
        self.counters["turns"] += 1  # type: ignore[attr-defined]
        self.counters["clarifications"] += 1  # type: ignore[attr-defined]
        try:
            stage = str(getattr(self.ears,  # type: ignore[attr-defined]
                                "last_stage", ""))
        except Exception:  # noqa: BLE001 -- stage tag is cosmetic only
            stage = ""
        try:
            self.ears.last_stage = (  # type: ignore[attr-defined]
                f"{tag}+{stage}")
        except Exception:  # noqa: BLE001 -- stage tag is cosmetic only
            pass
        record = {"kind": "clarify", "text": reply}
        self.last_records = [record]  # type: ignore[attr-defined]
        said = [line for line in
                (self.mouth.say(record)  # type: ignore[attr-defined]
                 for record in [record]) if line]
        self.experience.append(  # type: ignore[attr-defined]
            {"tick": self.tick, "kind": "turn", "text": text,  # type: ignore[attr-defined]
             "statuses": [r.get("status", r["kind"]) for r in [record]]})
        return self._event(A.LISTENING,  # type: ignore[attr-defined]
                           {"turn": text, "records": [record]}, said)
