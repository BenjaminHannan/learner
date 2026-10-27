#!/usr/bin/env python3
"""Experiment 162 -- THE ONE CHANGE: a possessive frame for "The"-initial names.

Director probe 03:45 on loop150 and loop137: "The Hobbit's author is
Tolkien.", "The Beatles' drummer is Ringo Starr.", "The Guardian's editor
is Kath Viner." On loop150 the office catch-all ``The (.+?) is (.+?)``
(scripts/fable_bench73_english_arm.py line 127) swallows them and stores a
WRONG write ("Hobbit's author", officeholder, "Tolkien" -- the "The" is
dropped); on loop135 (officeholder guard, scripts/fable_fix135_office.py
hear_teach135 at line 175, OfficeholderGuardMixin.hear at line 205,
artifacts/fable-fix135-20260922/) a refusal. Either way the fact cannot be
taught, so chains through works/bands/papers break.

THE ONE CHANGE: before the office catch-all, a possessive frame for
"The"-initial names (stackable mixin TheName162Mixin, outer-ears level like
the 155 mixin):

    teach: "The X's R is V." / "The Xs' R is V."

where R normalises to a key in the loop's own relation tables (union of the
bench73/bench92 cue-table keys + the FakeEars person table, minus the
exp-135 office family; same ALLOWED_KEYS construction as exp 155) and is
not an exp-135 office head -> save (The X, R, V) with "The" kept as part of
the name, via Bench73Stage._teach_action (structured teach, is_person=True
like every bench value, so values are entities and mid-chain hops work),
guarded by the loop121 value screen, the loop102 hearsay-subject check and
the 150 subject screen; the loop _act guards (139b value + 150 subject)
still apply. Anything else (relations outside the tables such as
drummer/editor/manager/mood, office Rs such as president/mayor, hedged or
two-fact turns) falls through to the base path untouched.

    ask: "Who is The X's R ...?" (singular 's and plural s' possessive
    chains) / "Who is the R of The X ...?" (of-form, optional trailing
    possessive chain)

resolves the leading "The X" (case of "the" ignored, via the notebook's own
case-insensitive resolve) to the taught entity and returns the equivalent
FakeEars ask (same act/name/relations/stage the base would build for a
one-word name). Asks whose entity does not resolve to exactly one taught
entity fall through to the base path untouched.

Office phrases ("The president of Zorvia is Mel Ash", "The mayor of Leeds
is Ann" -- no possessive) never match either frame and behave exactly as on
the base stack.

No existing file is edited. Everything new lives in this file (+
scripts/fable_loop162_agent.py, which stacks this mixin onto loop150
together with the 135 mixin).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (PERSON table, FakeEars, read-only)
import fable_bench73_english_arm as B73  # noqa: E402 (cue tables, read-only)
import fable_bench92_english_arm as B92  # noqa: E402 (cue tables, read-only)
import fable_fix135_office as F135  # noqa: E402 (office family, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject screen, read-only)
import fable_loop102_agent as L102  # noqa: E402 (hearsay checks, read-only)
import fable_loop121_agent as L121  # noqa: E402 (value screen, read-only)
import fable_loop90_agent as L90  # noqa: E402 (Bench73Stage, read-only)

# ----------------------------------------------------------------------------
# The loop's own relation tables (mechanical union, same construction as 155).
# ----------------------------------------------------------------------------
TABLE_KEYS: frozenset = frozenset(
    set(getattr(B73, "REL_MENTION_CUES", {}))
    | set(getattr(B92, "REL_CUES92", {}))
    | set(getattr(B92, "EXTRA_REL_CUES", {})))
PERSON_KEYS: frozenset = frozenset(A.PERSON_RELATIONS)
OFFICE_KEYS: frozenset = frozenset(F135.OFFICE_RELATIONS)
ALLOWED_KEYS: frozenset = (TABLE_KEYS | PERSON_KEYS) - OFFICE_KEYS

# Relation surface shape: letters/spaces/slash/hyphen only (same as 155).
_REL_SHAPE = re.compile(r"[A-Za-z][A-Za-z /-]*")

# Teach frame (strict full-turn): "The <X-inner>('s|s') <R> is <V>".
# Leading "The" is capital (like the base catch-all); the trailing period is
# stripped before matching. Correction prefixes are stripped first (the
# correct-vs-teach decision is Bench73Stage._teach_action's, by existing row).
_TEACH = re.compile(r"The\s+(.+?)('s|s')\s+(.+?)\s+is\s+(.+?)\s*$",
                    re.DOTALL)
_CORRECTION_LEAD = re.compile(r"^(actually\s*,|actually\s+|no\s*,|no\s+)(.+)$",
                              re.IGNORECASE | re.DOTALL)
_ASK_LEAD = re.compile(
    r"^(who|what|where)\s+(is|are)\s+(.+?)\s*\??\s*$",
    re.IGNORECASE | re.DOTALL)
_OF_FORM = re.compile(
    r"^the\s+(.+?)\s+of\s+(The\s+.+?)\s*$",
    re.IGNORECASE | re.DOTALL)
# Possessive link splitter: singular 's AND plural s' (apostrophe after a
# trailing s, followed by space/end). "The Beatles' founder's mother" ->
# ["The Beatles", "founder", "mother"].
_POSS_SPLIT = re.compile(r"['\u2019]s\b\s*|(?<=s)['\u2019](?=\s|$)")


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def relation_key(surface: str) -> str | None:
    """Relation surface -> loop relation key, or None when not allowed.

    Allowed = key in the loop's own tables (cue-table keys + person table),
    minus the office family; the surface must also not be an exp-135 office
    head (president/mayor/director/... stay on the base path exactly).
    Same gate as exp 155.
    """
    text = _norm(surface)
    if not _REL_SHAPE.fullmatch(text):
        return None
    key = "_".join(text.lower().split())
    if key not in ALLOWED_KEYS:
        return None
    if F135.is_office_head(text.lower()):
        return None
    return key


def parse_thename_teach(turn: str) -> dict | None:
    """Raw turn -> {name, key, Rsurf, V} or None.

    Strict full-turn match only; questions, forget shapes and correction-less
    non-frames never match. Returns None for relations outside the tables so
    the base path (135-guarded catch-all) owns those turns byte-identical.
    """
    text = _norm(turn)
    if not text or text.rstrip().endswith("?"):
        return None
    body = text
    if body.endswith(".") and not body.endswith(".."):
        body = body[:-1].strip()
    if not body:
        return None
    # Same trailing-qualifier strip the loop121 teach path applies, so a
    # qualified turn parses to the same value the base would store.
    body = L102.strip_trailing_qualifier(body)
    m = _CORRECTION_LEAD.match(body)
    if m and m.group(2).strip():
        body = m.group(2).strip()
    m = _TEACH.fullmatch(body)
    if m is None:
        return None
    inner, apos, rsurf, val = (m.group(1).strip(), m.group(2),
                               m.group(3).strip(), m.group(4).strip())
    if not inner or not rsurf or not val:
        return None
    if apos == "s'":
        # Plural possessive: the stem must end in s ("Beatles", "Times").
        if not inner.lower().endswith("s"):
            return None
        name = "The " + inner
    else:
        name = "The " + inner
    if "?" in val or ";" in val or "?" in name:
        return None
    key = relation_key(rsurf)
    if key is None:
        return None
    return {"name": _norm(name), "key": key, "Rsurf": _norm(rsurf),
            "V": val}


def _split_possessive(inner: str) -> list[str] | None:
    """"The Beatles' founder's mother" -> ["The Beatles", "founder", ...]."""
    parts = [p.strip() for p in _POSS_SPLIT.split(inner) if p.strip()]
    if len(parts) < 2:
        return None
    head = parts[0]
    m = re.match(r"^([Tt]he)\s+(.+)$", head, re.DOTALL)
    if m is None or not m.group(2).strip():
        return None
    return ["The " + m.group(2).strip()] + parts[1:]


def parse_thename_ask(turn: str) -> dict | None:
    """Raw turn -> {name, relations} or None.

    Possessive chains ("Who is The X's R1's R2?") and the of-form ("Who is
    the R of The X ...?", optional trailing possessive chain). The leading
    "The" of the entity may be any case; resolution to a taught entity
    happens in the mixin (needs the notebook), not here.
    """
    text = _norm(turn)
    if not text:
        return None
    m = _ASK_LEAD.match(text)
    if m is None:
        return None
    body = m.group(3).strip()
    if not body:
        return None
    relations: list[str] = []
    head_parts: list[str] | None = None
    mo = _OF_FORM.fullmatch(body)
    if mo is not None:
        outer_key = relation_key(mo.group(1).strip())
        if outer_key is None:
            return None
        head_parts = _split_possessive(mo.group(2).strip())
        if head_parts is None:
            # Bare "the R of The X" with no further possessive.
            tail = _norm(mo.group(2).strip())
            mhead = re.match(r"^[Tt]he\s+(.+)$", tail, re.DOTALL)
            if mhead is None or not mhead.group(1).strip():
                return None
            head_parts = ["The " + mhead.group(1).strip()]
        relations = [A.FakeEars._relation(p) for p in head_parts[1:]]
        relations.append(outer_key)
        name = head_parts[0]
    else:
        head_parts = _split_possessive(body)
        if head_parts is None:
            return None
        name = head_parts[0]
        relations = [A.FakeEars._relation(p) for p in head_parts[1:]]
    if not relations or len(relations) > A.MAX_HOPS:
        return None
    if any(not r for r in relations):
        return None
    return {"name": name, "relations": relations}


class TheName162Mixin:
    """Stackable mixin: possessive teaches/asks for "The"-initial names.

    Cooperative: the teach frame is matched BEFORE the base hear (the base
    would route it to the officeholder catch-all); the ask frame is matched
    before the base hear too, but only claims the turn when the entity
    resolves to exactly one taught entity, else the base owns it
    byte-identical. Same shape as InvertedFrame155Mixin.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        # ---- teach side: before the office catch-all ----
        parsed = parse_thename_teach(turn)
        if parsed is not None and nb is not None:
            if not L102.subject_is_hearsay_shaped(parsed["name"]):
                if L121.screen_value_121(parsed["V"]) is None:
                    verdict, payload = S150.screen_subject_150(
                        parsed["name"])
                    if verdict == "store":
                        stage = L90.Bench73Stage()
                        stage.bind(nb)
                        action = stage._teach_action(
                            (payload, parsed["key"], parsed["V"]))
                        # Bench parity: every bench value is entity-like, so
                        # mid-chain hops stay entity-valued (this is what the
                        # T2 chain needs; display triples are identical).
                        action["is_person"] = True
                        action["stage"] = "loop162"
                        self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                            "loop162-thename", 1.0)
                        return [action]
            return super().hear(turn)  # type: ignore[misc]
        # ---- ask side: only when the entity resolves ----
        qparsed = parse_thename_ask(turn)
        if qparsed is not None and nb is not None:
            try:
                found = nb.resolve(qparsed["name"])
            except Exception:
                found = None
            if (found is not None and found.status == "OK"
                    and found.detail.get("entity_id")):
                display = nb.entities.get(found.detail["entity_id"],
                                          qparsed["name"])
                action = {"act": "ask", "name": display,
                          "relations": list(qparsed["relations"]),
                          "stage": "fake"}
                self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                    "loop162-thename", 1.0)
                return [action]
            return super().hear(turn)  # type: ignore[misc]
        return super().hear(turn)  # type: ignore[misc]
