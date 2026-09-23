#!/usr/bin/env python3
"""Experiment 173 -- THE ONE CHANGE: the agent learns the user's own name.

Ben's ruling: "me" is the single user (loop166's USER entity). Versus
loop166, exactly one behaviour changes: a user-name statement sets the USER
entity's name, and user-name questions answer it.

Statement shapes (optional leading "Hi,/Hello,/Hey," greeting, optional
final punctuation):
    "My name is X", "I'm X", "I am X", "Call me X", "You can call me X",
where X is 1-3 capitalised name-shaped tokens. A token whose lowercase form
is in /usr/share/dict/words and is not a given name is NOT name-shaped, so
"I'm Tired" / "I am Happy" never name. Lowercase X after "My name is" /
"Call me" ("my name is sam") is capitalised silently; lowercase X after
"I'm" / "I am" is NEVER a name ("i'm tired", "I am from Oslo", "I'm
a teacher", "I am Kim's sister" stay on the loop166 path byte-identically).

Question shapes (optional trailing "?"):
    "What is my name?", "What's my name?", "Who am I?",
    "Do you know my name?", "what is my name"
-> "Your name is X." when set; "I don't know your name yet." when unset
(the loop166 unknown-form for first-person asks, instantiated for name).

A second, different name is taught with act="teach" (never "correct"), so
the notebook's functional-relation CONFLICT fires and the turn takes the
EXISTING listening change-prompt path ("I have your name as Sam. Do you
want me to change it to Max?"; yes replaces, no keeps). Never a silent
replace. Duplicate same-name teaches hit DUPLICATE_OK ("I already have
that."), exactly like any re-taught fact.

After naming, third-person turns whose possessive head IS the stored name
("Nell's sister is Ida.", "Who is Nell's sister?") are re-dispatched with
the head rewritten to "my", so they store/answer the SAME USER facts as
the first-person forms. "Is X <Owner>'s <R>?" is answered by looking up
(<Owner>, <R>) and comparing to X (yes/no/unknown with existing wordings).

No existing file is edited. Reply rendering reuses loop166's
rewrite_me166_reply (USER -> your/Your + " yet." rule), extended in
scripts/fable_loop173_agent.py to "yes"/"no" turns that complete a pending
name change (their replies can contain the raw key).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (FakeEars shapes, read-only)
import fable_fix166_me as M166  # noqa: E402 (USER key, screens, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject screen)
import fable_fix162_thename as T162  # noqa: E402 (correction lead)
import fable_loop102_agent as L102  # noqa: E402 (hearsay + qualifier)
import fable_loop121_agent as L121  # noqa: E402 (value screen)
import fable_loop90_agent as L90  # noqa: E402 (Bench73Stage teach action)

NAME_REL = "name"

_WORDS_PATH = Path("/usr/share/dict/words")


def _load_words() -> frozenset:
    try:
        return frozenset(
            ln.strip().lower() for ln in
            _WORDS_PATH.read_text(encoding="utf-8").splitlines()
            if ln.strip() and ln.strip().isalpha())
    except OSError:
        return frozenset()


WORDS = _load_words()

# Genuine given names (lowercase). A capitalised token counts as
# name-shaped when its lowercase form is absent from /usr/share/dict/words
# OR present here. This list holds only real given names -- never ordinary
# vocabulary (tired/happy/later/nurse/teacher/friend/sick/important/...).
GIVEN_NAMES = frozenset("""
sam dara nell dee ida max zara felix noor petra hugo milo rita ada
anna lee mia jo mary jane elena maria marcus sonia pavel greta omar priya
tomas lena kira yusuf theo nina omar hugo elsa rami sara liv asa eli ruth
amos irene otis alma hugo clara finn esme jude ivy kai luna miles nora owen
piper quinn rosa seth tess uma vera willa xena yara zane ash brooke caleb
dawn eliot flora graham hazel ivan jade kaya liam mona nadia oscar paula
ren sion tara ulf veda wren yasmin zeke abel bianca cyrus dora emmett faye
gus harriet ike josie kurt lena mo nels opal perry rhys sadie tate uri viv
wes yolanda yosef zelda aaron bella connor delia edith frankie gemma hank
iris jack kara leo molly nate olive pearl rex ruby simon tessa ursula vince
wendy xavier yvette zach eva ian ben dee nell
""".split())

_GREET = re.compile(r"^(hi|hello|hey),\s*(.*)$",
                    re.IGNORECASE | re.DOTALL)
_GREET_BARE = re.compile(r"^(hi|hello|hey)\s+(.*)$",
                         re.IGNORECASE | re.DOTALL)

_STMT_MYNAME = re.compile(r"^my\s+name\s+is\s+(.+)$",
                          re.IGNORECASE | re.DOTALL)
_STMT_IM = re.compile(r"^i(?:'m|’m|\s+am)\s+(.+)$",
                      re.IGNORECASE | re.DOTALL)
_STMT_CALL = re.compile(r"^(?:you\s+can\s+)?call\s+me\s+(.+)$",
                        re.IGNORECASE | re.DOTALL)

_Q_MYNAME = re.compile(
    r"^(?:what\s+is\s+my\s+name|what's\s+my\s+name|who\s+am\s+i|"
    r"do\s+you\s+know\s+my\s+name)\s*$", re.IGNORECASE | re.DOTALL)

_TOKEN = re.compile(r"^[A-Za-z][A-Za-z\-]*$")
_YESNO = re.compile(r"^(yes|no)\s*\.?\s*$", re.IGNORECASE)
_CHECK = re.compile(r"^is\s+(.+?)\s+(.+?)\s*$",
                    re.IGNORECASE | re.DOTALL)


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def _strip_outer(turn: str) -> str:
    """Strip greeting, trailing punctuation, correction lead. Returns body."""
    text = _norm(turn)
    if not text:
        return ""
    body = text
    if body.endswith((".", "!", "?")) and not body.endswith(".."):
        body = body[:-1].strip()
    m = _GREET.match(body) or _GREET_BARE.match(body)
    if m and m.group(2).strip():
        body = m.group(2).strip()
        if body.endswith((".", "!", "?")) and not body.endswith(".."):
            body = body[:-1].strip()
    if not body:
        return ""
    return body


def is_name_shaped(token: str) -> bool:
    """Capitalised token that is not ordinary vocabulary."""
    if not _TOKEN.fullmatch(token):
        return False
    if "'" in token:
        return False
    if not token[0].isupper():
        return False
    low = token.lower()
    return low not in WORDS or low in GIVEN_NAMES


def canonical_name(raw: str, capitalise_lower: bool) -> str | None:
    """1-3 tokens -> canonical name, or None when not name-shaped."""
    parts = _norm(raw).split()
    if not (1 <= len(parts) <= 3):
        return None
    out = []
    for tok in parts:
        if "'" in tok or not _TOKEN.fullmatch(tok):
            return None
        if not tok[0].isupper():
            if not capitalise_lower:
                return None
            tok = tok[0].upper() + tok[1:]
        if not is_name_shaped(tok):
            return None
        out.append(tok[0].upper() + tok[1:])
    return " ".join(out)


def parse_name_statement(turn: str) -> dict | None:
    """Raw turn -> {"name": X} or None. Pure function (no notebook)."""
    text = _norm(turn)
    if not text or text.rstrip().endswith("?"):
        return None
    body = _strip_outer(text)
    if not body:
        return None
    # A correction lead ("Actually, my name is Max.") still names -- but it
    # must take the change-prompt path, never a silent replace, so the lead
    # is stripped and the remainder is treated as a plain (non-correction)
    # name statement.
    m = T162._CORRECTION_LEAD.match(body)
    if m and m.group(2).strip():
        body = m.group(2).strip()
    m = _STMT_MYNAME.match(body)
    if m:
        name = canonical_name(m.group(1), capitalise_lower=True)
        return {"name": name} if name else None
    m = _STMT_CALL.match(body)
    if m:
        name = canonical_name(m.group(1), capitalise_lower=True)
        return {"name": name} if name else None
    m = _STMT_IM.match(body)
    if m:
        name = canonical_name(m.group(1), capitalise_lower=False)
        return {"name": name} if name else None
    return None


def parse_name_question(turn: str) -> dict | None:
    """Raw turn -> {} for a user-name question, else None. Pure."""
    text = _norm(turn)
    if not text:
        return None
    body = _strip_outer(text)
    if not body:
        return None
    if _Q_MYNAME.match(body):
        return {}
    return None


def current_name(nb) -> str | None:
    """The USER entity's taught name value (literal or entity display)."""
    try:
        found = nb.resolve(M166.USER_KEY)
    except Exception:  # noqa: BLE001
        return None
    if found.status != "OK":
        return None
    eid = found.detail["entity_id"]
    try:
        rows = nb.current(eid, NAME_REL)
    except Exception:  # noqa: BLE001
        return None
    for row in rows:
        if row.get("source") != "taught":
            continue
        val = row.get("value")
        if isinstance(val, dict):
            if "literal" in val and str(val["literal"]).strip():
                return str(val["literal"]).strip()
            ent = val.get("entity")
            if ent and ent in nb.entities:
                return str(nb.entities[ent])
        elif isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _head_is_name(head: str, name: str) -> bool:
    return _norm(head).lower() == _norm(name).lower()


def parse_x_teach(turn: str, name: str) -> str | None:
    """Third-person teach headed by the stored name -> rewritten "my" turn."""
    text = _norm(turn)
    if not text or text.rstrip().endswith("?"):
        return None
    body = text
    if body.endswith(".") and not body.endswith(".."):
        body = body[:-1].strip()
    if not body:
        return None
    m = re.match(r"^(.+?)\s+is\s+(.+?)\s*$", body,
                 re.IGNORECASE | re.DOTALL)
    if m is None:
        return None
    left, val = m.group(1).strip(), m.group(2).strip()
    if not left or not val:
        return None
    parts = [p.strip() for p in re.split(A._APOS, left) if p.strip()]
    if len(parts) < 2:
        return None
    if not _head_is_name(parts[0], name):
        return None
    rest = "'s ".join(parts[1:])
    return "My %s is %s." % (rest, val)


def parse_x_ask(turn: str, name: str) -> str | None:
    """Third-person ask headed by the stored name -> rewritten "my" turn."""
    text = _norm(turn)
    if not text:
        return None
    m = re.match(r"^(who|what|where)\s+(is|are)\s+(.+?)\s*\??\s*$", text,
                 re.IGNORECASE | re.DOTALL)
    if m is None:
        return None
    parts = [p.strip() for p in re.split(A._APOS, m.group(3))
             if p.strip()]
    if len(parts) < 2:
        return None
    if not _head_is_name(parts[0], name):
        return None
    rest = "'s ".join(parts[1:])
    return "%s %s my %s?" % (m.group(1), m.group(2), rest)


def parse_name_check(turn: str, name: str) -> dict | None:
    """'Is X <Owner>'s <R>?' with X == stored name -> check triple."""
    text = _norm(turn)
    if not text:
        return None
    m = _CHECK.fullmatch(_strip_outer(text))
    if m is None:
        return None
    who, rest = m.group(1).strip(), m.group(2).strip()
    if not _head_is_name(who, name):
        return None
    parts = [p.strip() for p in re.split(A._APOS, rest) if p.strip()]
    if len(parts) != 2:
        return None
    owner, rel = parts
    if not owner or not rel or " " in rel.strip():
        return None
    key = M166.canonical_relation(rel)
    if key is None:
        return None
    return {"owner": owner, "relation": key,
            "Rsurf": _norm(rel), "x": name}


class Name173Mixin:
    """Stackable mixin: user-name frames before the loop166 stages.

    Cooperative: name statements/questions, stored-name-headed possessive
    turns, and "Is X ...?" checks are claimed here; EVERYTHING else falls
    through to super().hear() untouched, so non-name behaviour is the
    loop166 code literally.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        if nb is None:
            return super().hear(turn)  # type: ignore[misc]
        # ---- user-name statement: sets USER's name (change-prompt path) ----
        parsed = parse_name_statement(turn)
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
                        # NOT "correct": a different second name must hit
                        # the listening CONFLICT change-prompt, never a
                        # silent supersede. Literal value: a name statement
                        # creates no new non-USER entity (T2).
                        action["act"] = "teach"
                        action["is_person"] = False
                        action["stage"] = "loop173"
                        action["name173"] = True
                        self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                            "loop173-name", 1.0)
                        return [action]
            return super().hear(turn)  # type: ignore[misc]
        # ---- user-name question: answers USER's name ----
        if parse_name_question(turn) is not None:
            action = {"act": "ask", "name": M166.USER_KEY,
                      "relations": [NAME_REL],
                      "stage": "fake", "name173": True}
            self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                "loop173-name", 1.0)
            return [action]
        # ---- stored-name-headed turns resolve to the USER entity ----
        knob = current_name(nb)
        if knob:
            rewritten = parse_x_teach(turn, knob)
            if rewritten is not None:
                actions = super().hear(rewritten)  # type: ignore[misc]
                for a in actions:
                    if isinstance(a, dict):
                        a["name173"] = True
                self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                    "loop173-xhead", 1.0)
                return actions
            rewritten = parse_x_ask(turn, knob)
            if rewritten is not None:
                actions = super().hear(rewritten)  # type: ignore[misc]
                for a in actions:
                    if isinstance(a, dict):
                        a["name173"] = True
                self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                    "loop173-xhead", 1.0)
                return actions
            checked = parse_name_check(turn, knob)
            if checked is not None:
                self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                    "loop173-namecheck", 1.0)
                return [{"act": "namecheck",
                         "owner": checked["owner"],
                         "relations": [checked["relation"]],
                         "x": checked["x"],
                         "stage": "loop173", "name173": True}]
        return super().hear(turn)  # type: ignore[misc]
