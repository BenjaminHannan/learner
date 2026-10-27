#!/usr/bin/env python3
"""Experiment 173b -- THE ONE CHANGE vs loop173: word-names count as names.

Versus loop173 (scripts/fable_fix173_username.py, read-only, never edited),
exactly one behaviour changes: the name-shape test for user-name statements
only. Everything else (questions, x-heads, namecheck, replies, gates) is
loop173's code literally.

Rule 173b, sealed before any registered run:

(a) After "My name is" / "Call me" / "You can call me" (the frame itself
    says it is a name), a value of 1-3 letter tokens counts as a name EVEN
    IF its words are in /usr/share/dict/words, EXCEPT:
    - the sealed closed list CLOSED_173B (36 phrases, lowercase, whole-value
      match after norm), which holds only non-name words/phrases, never
      real names; and
    - values containing a determiner (DETERMINERS_173B = {a, an, the},
      case-insensitive, any token) or a digit (any char 0-9).
    Lowercase values after "My name is" are capitalised silently (as in
    173). After "Call me" / "You can call me", Title-case is REQUIRED
    (every token already capitalised); lowercase "Call me later" /
    "call me back" therefore stay on the loop173 path identically.
(b) After "I'm" / "I am", 173's conservative rule is KEPT (states are
    common), but the given-name list becomes 173's GIVEN_NAMES PLUS
    /usr/share/dict/propernames (1,308 lines). Lowercase after I'm/I am is
    still NEVER a name.

Evidence note (verified pre-seal on this Mac): all 16 T1c word-names are in
/usr/share/dict/words; propernames (lowercased) contains grace/dawn/rich/
grant/will/mark/aaron but NOT maya/rose/rue/sol/pip/hope/faith/iris/sky/
reed. Hence "I'm Grace." DOES name in 173b (brief's "may still not name"
is superseded by evidence; the accepted known miss after I'm is
maya/rose/rue/sol/pip/hope/faith/iris/sky/reed).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix173_username as N173  # noqa: E402 (base shapes, read-only)
import fable_loop166_agent as L166  # noqa: E402 (bypass target, read-only)
import fable_agent_loop as A  # noqa: E402 (FakeEars shapes, read-only)
import fable_fix166_me as M166  # noqa: E402 (USER key, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject screen)
import fable_loop102_agent as L102  # noqa: E402 (hearsay screen)
import fable_loop121_agent as L121  # noqa: E402 (value screen)
import fable_loop90_agent as L90  # noqa: E402 (teach action)

NAME_REL = N173.NAME_REL

_PROPER_PATH = Path("/usr/share/dict/propernames")


def _load_proper() -> frozenset:
    try:
        return frozenset(
            ln.strip().lower() for ln in
            _PROPER_PATH.read_text(encoding="utf-8").splitlines()
            if ln.strip() and ln.strip().isalpha())
    except OSError:
        return frozenset()


PROPER_173B = _load_proper()
GIVEN_173B = frozenset(N173.GIVEN_NAMES) | PROPER_173B

# Sealed closed list: non-name words/phrases only (whole-value, lowercase).
# Never a real name. Count = 37 (>= 30 required).
CLOSED_173B = frozenset([
    "not", "not important", "a secret", "secret", "unknown", "none",
    "nothing", "later", "back", "anytime", "whatever", "anything",
    "maybe", "tomorrow", "soon", "crazy", "stupid", "lazy", "a nurse",
    "nurse", "tired", "happy", "sick", "a teacher", "teacher",
    "from oslo", "important", "nobody", "no one", "anyone", "someone",
    "sorry", "please", "hello", "hi", "a friend", "the boss", "my friend",
])

DETERMINERS_173B = frozenset({"a", "an", "the"})


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def _has_digit(raw: str) -> bool:
    return any(ch.isdigit() for ch in str(raw))


def _has_determiner(parts: list[str]) -> bool:
    return any(p.lower() in DETERMINERS_173B for p in parts)


def is_name_shaped_173b_im(token: str) -> bool:
    """173's conservative test, with the extended given list (I'm only)."""
    if not N173._TOKEN.fullmatch(token):
        return False
    if "'" in token:
        return False
    if not token[0].isupper():
        return False
    low = token.lower()
    return low not in N173.WORDS or low in GIVEN_173B


def canonical_name_173b(raw: str, frame: str) -> str | None:
    """1-3 letter tokens -> canonical name, or None. Frame-aware.

    frame: "myname" (capitalise lower), "call" (Title-case required),
    "im" (173 conservative + extended list, never capitalise).
    Closed/determiner/digit screens apply to myname/call frames.
    """
    parts = _norm(raw).split()
    if not (1 <= len(parts) <= 3):
        return None
    if _has_digit(raw):
        return None
    if frame in ("myname", "call"):
        if _has_determiner(parts):
            return None
        if _norm(raw).lower() in CLOSED_173B:
            return None
        out = []
        for tok in parts:
            if "'" in tok or not N173._TOKEN.fullmatch(tok):
                return None
            if frame == "myname":
                if not tok[0].isupper():
                    tok = tok[0].upper() + tok[1:]
            else:  # call: Title-case required
                if not tok[0].isupper():
                    return None
            out.append(tok[0].upper() + tok[1:])
        return " ".join(out)
    if frame == "im":
        out = []
        for tok in parts:
            if "'" in tok or not N173._TOKEN.fullmatch(tok):
                return None
            if not tok[0].isupper():
                return None
            if not is_name_shaped_173b_im(tok):
                return None
            out.append(tok[0].upper() + tok[1:])
        return " ".join(out)
    return None


def parse_name_statement_173b(turn: str) -> dict | None:
    """Raw turn -> {"name": X, "frame": f} or None. Pure function."""
    text = _norm(turn)
    if not text or text.rstrip().endswith("?"):
        return None
    body = N173._strip_outer(text)
    if not body:
        return None
    import fable_fix162_thename as T162  # local import (read-only)
    m = T162._CORRECTION_LEAD.match(body)
    if m and m.group(2).strip():
        body = m.group(2).strip()
    m = N173._STMT_MYNAME.match(body)
    if m:
        name = canonical_name_173b(m.group(1), "myname")
        return {"name": name, "frame": "myname"} if name else None
    m = N173._STMT_CALL.match(body)
    if m:
        name = canonical_name_173b(m.group(1), "call")
        return {"name": name, "frame": "call"} if name else None
    m = N173._STMT_IM.match(body)
    if m:
        name = canonical_name_173b(m.group(1), "im")
        return {"name": name, "frame": "im"} if name else None
    return None


class Name173bMixin:
    """Stackable mixin vs loop173: 173b name-shape only, else loop166 path.

    NOT a subclass of Name173Mixin (avoids double-claim): name statements
    are handled here with the 173b parser; a turn 173 would claim but 173b
    rejects (Call-me-lowercase, exactly S13) bypasses loop173's stage to
    Loop166Ears directly; everything else delegates to super() (loop173),
    whose question/x-head/namecheck/fallthrough behaviour is unchanged.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        if nb is None:
            return super().hear(turn)  # type: ignore[misc]
        parsed = parse_name_statement_173b(turn)
        if parsed is not None:
            if not L102.subject_is_hearsay_shaped(M166.USER_KEY):
                if L121.screen_value_121(parsed["name"]) is None:
                    verdict, payload = S150.screen_subject_150(
                        M166.USER_KEY)
                    if verdict == "store":
                        stage = L90.Bench73Stage()
                        stage.bind(nb)
                        action = stage._teach_action(
                            (payload, NAME_REL, parsed["name"]))
                        action["act"] = "teach"
                        action["is_person"] = False
                        action["stage"] = "loop173b"
                        action["name173"] = True
                        action["name173b"] = True
                        self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                            "loop173b-name", 1.0)
                        return [action]
            return super().hear(turn)  # type: ignore[misc]
        # 173-accept but 173b-reject -> bypass loop173's name stage.
        try:
            legacy = N173.parse_name_statement(turn)
        except Exception:  # noqa: BLE001
            legacy = None
        if legacy is not None:
            return L166.Loop166Ears.hear(self, turn)  # type: ignore[arg-type]
        # Questions, x-heads, namecheck: loop173's code literally.
        return super().hear(turn)  # type: ignore[misc]
