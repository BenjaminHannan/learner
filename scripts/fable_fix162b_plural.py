#!/usr/bin/env python3
"""Experiment 162b -- THE ONE CHANGE: plural "The Xs' R is V." saves (The Xs, R, V).

Follow-up to the registered FAIL of exp 162
(artifacts/fable-thename162-20260922/RESULTS.md, diagnosis note 1):
the teach regex ``The\\s+(.+?)('s|s')\\s+...`` (scripts/fable_fix162_thename.py)
consumes the stem-final "s" into the ``s'`` branch, so "The Beatles' founder
is Lennon." parses as stem "Beatle" + ``s'``; the stem guard
(``endswith("s")``) then rejects EVERY plural and the turn falls through to
the base refusal. Singular path is 19/19.

THE ONE CHANGE (behaviour): plural possessives "The Xs' R is V." save subject
"The Xs" (name = stem + "s") through the same canonical path (162's
relation-key gate, loop121 value screen, loop102 hearsay check, 150 subject
screen, Bench73Stage._teach_action with is_person=True). Singular behaviour
is byte-identical to loop162 BY CONSTRUCTION: the mixin below only claims
turns whose possessive marker is the plural ``s'`` branch (which loop162
always rejects), and delegates every other turn to TheName162Mixin
untouched.

Also in this file: nothing else. The daemon wrapper fix lives in
scripts/fable_loop162b_agent.py (harness only, disclosed in RESULTS.md).

No existing file is edited. Base modules are imported read-only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix162_thename as T162  # noqa: E402 (base mixin + tables, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject screen, read-only)
import fable_loop102_agent as L102  # noqa: E402 (hearsay + qualifier, read-only)
import fable_loop121_agent as L121  # noqa: E402 (value screen, read-only)
import fable_loop90_agent as L90  # noqa: E402 (Bench73Stage, read-only)


def parse_plural_teach(turn: str) -> dict | None:
    """Raw turn -> {name, key, Rsurf, V} for plural "The Xs' R is V." or None.

    Same strict full-turn shape as T162.parse_thename_teach (trailing "."
    strip, loop121 trailing-qualifier strip, correction-prefix strip, relation
    surface shape + ALLOWED_KEYS gate + office-head veto, "?" / ";" veto),
    except only the plural ``s'`` marker is accepted and the saved name is
    stem + "s" ("The Beatles"), which is what the marker consumed.
    Singular "'s" turns ALWAYS return None here (the base 162 mixin owns
    them byte-identical).
    """
    text = T162._norm(turn)
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
    m = T162._TEACH.fullmatch(body)
    if m is None:
        return None
    inner, apos, rsurf, val = (m.group(1).strip(), m.group(2),
                               m.group(3).strip(), m.group(4).strip())
    if apos != "s'":
        return None  # singular "'s" (or anything else): not ours, ever
    if not inner or not rsurf or not val:
        return None
    # THE ONE CHANGE: the regex consumed the stem-final "s" into the ``s'``
    # marker, so the subject is the stem + "s" (162 built "The " + stem and
    # then rejected it for not ending in "s").
    name = T162._norm("The " + inner + "s")
    if "?" in val or ";" in val or "?" in name:
        return None
    key = T162.relation_key(rsurf)
    if key is None:
        return None
    return {"name": name, "key": key, "Rsurf": T162._norm(rsurf), "V": val}


class Plural162bMixin:
    """Stackable mixin: plural teaches before the 162 stage, rest delegates.

    Cooperative: the plural frame is matched BEFORE the base hear (loop162
    would refuse it); anything this frame declines -- including every
    singular "'s" turn -- falls through to super().hear() untouched, so
    singular + office + ask behaviour is the loop162 code path literally.
    Same screens/save as 162 (121 value, 102 hearsay, 150 subject,
    Bench73Stage._teach_action, is_person=True); loop _act guards still apply.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        parsed = parse_plural_teach(turn)
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
                        action["is_person"] = True
                        action["stage"] = "loop162b"
                        self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                            "loop162b-plural", 1.0)
                        return [action]
            return super().hear(turn)  # type: ignore[misc]
        return super().hear(turn)  # type: ignore[misc]
