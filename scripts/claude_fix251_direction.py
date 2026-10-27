"""Exp 251 fix: verb-direction questions (question side only; never writes).

The leak (reproduced on base228, traced in design/v3/30-modes/251-direction-opus.md):
after "X's employer is Y.", the question "Who does X employ?" (also "Whom does
X employ?", "Who is employed by X?") is claimed by
scripts/fable_bench92_english_arm.py:221 compose_n_hop (called from
scripts/fable_loop138_agent.py:122). It finds the one mentioned entity X,
walks X's single outgoing relation (employer), and its coverage gate passes
because the cue "employ" (REL_CUES92["employer"], line 100) is a SUBSTRING of
the question. So the reply is X's own forward value -- the opposite direction.

This mixin sits OUTERMOST on the inner ears and claims only these "?" forms,
for the verbs in VERB251 (whose active subject is the VALUE side):

    Who/Whom does|do|did X <verb>?
    Who/Whom is|are|was|were <verb-ed> by X?
    What does|do|did X own? / What is ... owned by X?   (own only)

(optional leading "hi/hello/hey," and "please", optional trailing ", please").

  * X known (nb.resolve OK, or X equals a stored triple's subject/value,
    case-insensitive): answer from stored facts whose VALUE is X for that
    verb's relation(s): "X employs Y." + " (worked out backwards)". Never
    stored (clarify action only). None -> "I don't know who X employs."
  * X not known: the turn falls through to the unchanged stack; if the stack
    returns any "ask" action (which would read someone's forward value), it
    is replaced by the same decline. Any other result is left untouched.
X's own forward value is never read.

Extra direction wordings (found leaking on base228 through the same
compose_n_hop cue substrings; see the design note):
    Who works|worked for|at X?   Who is employed at X?          -> employer
    Who reports to X?  Who works under X?        -> manager/boss/supervisor
    Who studies under X?  Who learns from X?                     -> teacher
    Whose R is X?  Who is X the R of?                            -> R
    Who is/are X's employee(s)/staff/student(s)/patient(s)/...   -> mapped
For these the unchanged stack runs FIRST and is kept byte-identical unless
it returned an "ask" action (a forward read = the leak). Only then is the
reply replaced by the inverse answer (fact lines + label) or a decline.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop90_agent as L90  # noqa: E402 (read-only)

STAGE251 = "direction251"
LABEL251 = "(worked out backwards)"
USER_KEY251 = "USER"  # fable_fix166_me.py:49 (same as fable_fix221 USER_KEY221)

# verb -> (3rd person singular, past participle, relation keys stored as)
VERB251: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "employ": ("employs", "employed", ("employer",)),
    "hire": ("hires", "hired", ("employer",)),
    "teach": ("teaches", "taught", ("teacher",)),
    "coach": ("coaches", "coached", ("coach",)),
    "manage": ("manages", "managed", ("manager",)),
    "supervise": ("supervises", "supervised", ("supervisor",)),
    "treat": ("treats", "treated", ("doctor",)),
    "represent": ("represents", "represented", ("lawyer",)),
    "mentor": ("mentors", "mentored", ("mentor",)),
    "own": ("owns", "owned", ("owner",)),
}
_PP2VERB = {pp: v for v, (_s, pp, _r) in VERB251.items()}

_PRE = r"(?:(?:hi|hello|hey)\s*[,!]?\s+)?(?:please\s*,?\s+)?"
_SUF = r"(?:\s*,?\s*please)?"
_VERBS = "|".join(sorted(VERB251, key=len, reverse=True))
_PPS = "|".join(sorted(_PP2VERB, key=len, reverse=True))
_RX_ACTIVE = re.compile(
    rf"{_PRE}(?:who|whom)\s+(?:does|do|did)\s+(?P<X>.+?)\s+(?P<V>{_VERBS})"
    rf"{_SUF}\s*\?", re.IGNORECASE)
_RX_PASSIVE = re.compile(
    rf"{_PRE}(?:who|whom)\s+(?:is|are|was|were)\s+(?P<PP>{_PPS})\s+by\s+"
    rf"(?P<X>.+?){_SUF}\s*\?", re.IGNORECASE)
_RX_OWN = re.compile(
    rf"{_PRE}what\s+(?:(?:does|do|did)\s+(?P<X>.+?)\s+own|"
    rf"(?:is|are|was|were)\s+owned\s+by\s+(?P<X2>.+?)){_SUF}\s*\?",
    re.IGNORECASE)

_FIRST = {"i", "me"}

_BOSSY = ("manager", "boss", "supervisor")
_NOUN2RELS = {
    "employee": ("employer",), "employees": ("employer",),
    "staff": ("employer",), "worker": ("employer",), "workers": ("employer",),
    "student": ("teacher",), "students": ("teacher",),
    "pupil": ("teacher",), "pupils": ("teacher",),
    "patient": ("doctor",), "patients": ("doctor",),
    "client": ("lawyer",), "clients": ("lawyer",),
    "mentee": ("mentor",), "mentees": ("mentor",),
    "report": _BOSSY, "reports": _BOSSY,
    "subordinate": _BOSSY, "subordinates": _BOSSY,
}
_NOUNS = "|".join(sorted(_NOUN2RELS, key=len, reverse=True))
_X = r"(?P<X>.+?)"
# (regex, relations or None (= the captured R), decline format)
_EXTRA251 = [
    (re.compile(rf"{_PRE}who\s+(?:works|work|worked|is\s+working)\s+"
                rf"(?:for|at)\s+{_X}{_SUF}\s*\?", re.IGNORECASE),
     ("employer",), "I don't know who works for {X}."),
    (re.compile(rf"{_PRE}who\s+(?:is|are|was|were)\s+employed\s+at\s+"
                rf"{_X}{_SUF}\s*\?", re.IGNORECASE),
     ("employer",), "I don't know who works for {X}."),
    (re.compile(rf"{_PRE}who\s+(?:reports|report|reported)\s+to\s+"
                rf"{_X}{_SUF}\s*\?", re.IGNORECASE),
     _BOSSY, "I don't know who reports to {X}."),
    (re.compile(rf"{_PRE}who\s+(?:works|worked)\s+under\s+{_X}{_SUF}\s*\?",
                re.IGNORECASE),
     _BOSSY, "I don't know who works under {X}."),
    (re.compile(rf"{_PRE}who\s+(?:studies\s+under|studied\s+under|learns\s+"
                rf"from|learned\s+from|learnt\s+from)\s+{_X}{_SUF}\s*\?",
                re.IGNORECASE),
     ("teacher",), "I don't know who learns from {X}."),
    (re.compile(rf"{_PRE}whose\s+(?P<R>[a-z][a-z ]*?)\s+(?:is|was)\s+{_X}"
                rf"{_SUF}\s*\?", re.IGNORECASE),
     None, "I don't know anyone whose {R} is {X}."),
    (re.compile(rf"{_PRE}who\s+(?:is|was)\s+{_X}\s+the\s+(?P<R>[a-z][a-z ]*?)"
                rf"\s+of{_SUF}\s*\?", re.IGNORECASE),
     None, "I don't know anyone whose {R} is {X}."),
    (re.compile(rf"{_PRE}who\s+(?:is|are|was|were)\s+{_X}(?:'s|\u2019s|s')\s+"
                rf"(?P<N>{_NOUNS}){_SUF}\s*\?", re.IGNORECASE),
     "noun", "I don't know {X}'s {N}."),
]


def parse_extra251(turn: str):
    """'?' turn -> dict(X, rels, decline) for an extra direction wording."""
    t = " ".join(str(turn).split())
    if not t.endswith("?"):
        return None
    for rx, rels, fmt in _EXTRA251:
        m = rx.fullmatch(t)
        if not m:
            continue
        x = m.group("X").strip()
        if rels is None:
            r = " ".join(m.group("R").lower().split())
            rels = (r, r.replace(" ", "_"))
            dec = fmt.format(R=r, X=x)
        elif rels == "noun":
            n = m.group("N").lower()
            rels = _NOUN2RELS[n]
            dec = fmt.format(N=n, X=x)
        else:
            dec = fmt.format(X=x)
        return {"X": x, "rels": tuple(rels), "decline": dec}
    return None


def parse251(turn: str):
    """'?' turn -> (X as typed, verb) for a direction question, else None."""
    t = " ".join(str(turn).split())
    if not t.endswith("?"):
        return None
    m = _RX_ACTIVE.fullmatch(t)
    if m:
        return m.group("X").strip(), m.group("V").lower()
    m = _RX_PASSIVE.fullmatch(t)
    if m:
        return m.group("X").strip(), _PP2VERB[m.group("PP").lower()]
    m = _RX_OWN.fullmatch(t)
    if m:
        return (m.group("X") or m.group("X2")).strip(), "own"
    return None


def _norm(s) -> str:
    return " ".join(str(s).split()).strip().rstrip(".").lower()


def _triples(nb) -> list[tuple[str, str, str]]:
    try:
        return [tuple(x) for x in L90.notebook_triples(nb)]
    except Exception:  # noqa: BLE001
        return []


def known_name251(nb, x: str, triples) -> str | None:
    """Display name if X is a known name, else None. Known = nb.resolve OK,
    or X equals (case-insensitively) a stored triple's subject or value.
    A common lowercase word counts only if it IS such a stored name."""
    try:
        found = nb.resolve(x)
        if getattr(found, "status", None) == "OK":
            return str(found.detail.get("answer") or x)
    except Exception:  # noqa: BLE001
        pass
    want = _norm(x)
    for s, _r, o in triples:
        for cand in (s, o):
            if cand != USER_KEY251 and _norm(cand) == want:
                return str(cand).strip().rstrip(".")
    return None


def _join(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def direction_reply251(nb, x_disp: str, verb: str, triples) -> str:
    """Inverse answer over live taught facts (never stored), or decline."""
    s3, _pp, rels = VERB251[verb]
    want = _norm(x_disp)
    subs: list[str] = []
    for s, r, o in triples:
        if r in rels and _norm(o) == want:
            who = "you" if s == USER_KEY251 else str(s).strip()
            if who not in subs:
                subs.append(who)
    if subs:
        return f"{x_disp} {s3} {_join(subs)}. {LABEL251}"
    return decline251(x_disp, verb, triples)


def is_stored_value251(x: str, triples) -> bool:
    want = _norm(x)
    return any(_norm(o) == want for _s, _r, o in triples)


def decline251(x_typed: str, verb: str, triples=()) -> str:
    """"I don't know who X employs." -- except that a name which is itself
    a stored VALUE is not echoed back (so a decline can never repeat a
    stored value): "I don't know who they employ." """
    x = x_typed.strip()
    if x.lower() in _FIRST:
        return f"I don't know who you {verb}."
    if is_stored_value251(x, triples):
        return f"I don't know who they {verb}."
    return f"I don't know who {x} {VERB251[verb][0]}."


GENERIC_DECLINE251 = "I don't know that from what you taught me."


def extra_reply251(nb, x_disp: str | None, rels, decline: str,
                   triples) -> str:
    """Inverse fact lines over live taught facts (never stored) + label,
    or the form's decline."""
    if x_disp is not None:
        want = _norm(x_disp)
        lines: list[str] = []
        for s, r, o in triples:
            if r in rels and _norm(o) == want:
                who = "Your" if s == USER_KEY251 else f"{str(s).strip()}'s"
                line = f"{who} {str(r).replace('_', ' ')} is {x_disp}."
                if line not in lines:
                    lines.append(line)
        if lines:
            return " ".join(lines) + " " + LABEL251
    if x_disp is not None and is_stored_value251(x_disp, triples):
        return GENERIC_DECLINE251
    return decline


class Direction251Mixin:
    """Outermost stackable ears mixin (question side only; never writes)."""

    def _mark251(self, how: str) -> None:
        try:
            self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                f"{STAGE251}-{how}", 1.0)
        except AttributeError:
            pass

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        parsed = parse251(turn)
        nb = getattr(self, "nb", None)
        if nb is None:
            return super().hear(turn)  # type: ignore[misc]
        if parsed is None:
            extra = parse_extra251(turn)
            actions = super().hear(turn)  # type: ignore[misc]
            if extra is None or not isinstance(actions, list) or not any(
                    isinstance(a, dict) and a.get("act") == "ask"
                    for a in actions):
                return actions
            triples = _triples(nb)
            disp = known_name251(nb, extra["X"], triples)
            text = extra_reply251(nb, disp, extra["rels"], extra["decline"],
                                  triples)
            self._mark251("extra-" + ("inverse" if LABEL251 in text
                                      else "decline"))
            return [{"act": "clarify", "text": text, "direction251": "extra"}]
        x, verb = parsed
        triples = _triples(nb)
        disp = known_name251(nb, x, triples)
        if disp is not None:
            text = direction_reply251(nb, disp, verb, triples)
            self._mark251("inverse" if LABEL251 in text else "decline")
            return [{"act": "clarify", "text": text, "direction251": verb}]
        actions = super().hear(turn)  # type: ignore[misc]
        if isinstance(actions, list) and any(
                isinstance(a, dict) and a.get("act") == "ask"
                for a in actions):
            self._mark251("guard")
            return [{"act": "clarify",
                     "text": decline251(x, verb, _triples(nb)),
                     "direction251": verb}]
        return actions


def install_direction251(loop) -> None:
    """Put Direction251Mixin outermost on the loop's inner ears (idempotent).
    Instance-level class swap: every attribute of the built ears is kept."""
    ears = getattr(loop, "ears", None)
    inner = getattr(ears, "inner", None) or ears
    if inner is None or isinstance(inner, Direction251Mixin):
        return
    cls = inner.__class__
    inner.__class__ = type(f"Direction251_{cls.__name__}",
                           (Direction251Mixin, cls), {})
    notes = getattr(loop, "notes", None)
    if isinstance(notes, list):
        notes.append("fix251: Direction251Mixin outermost on inner ears")


def selftest251() -> int:
    ok = 0
    cases = [
        ("Who does Tamsin Orlo employ?", ("Tamsin Orlo", "employ")),
        ("whom does brenna tolk teach?", ("brenna tolk", "teach")),
        ("Who is employed by Tamsin Orlo?", ("Tamsin Orlo", "employ")),
        ("Hi, who was taught by Ardith, please?", ("Ardith", "teach")),
        ("What does Harbin Cole own?", ("Harbin Cole", "own")),
        ("Who employs Tamsin Orlo?", None),
        ("Who is Tamsin Orlo's employer?", None),
        ("Who does Tamsin Orlo work for?", None),
        ("Who does Tamsin Orlo employ.", None),
    ]
    extra = [("Who works for Corla Denning?", ("employer",)),
             ("Whose employer is Corla Denning?", ("employer",)),
             ("Who is Corla Denning the employer of?", ("employer",)),
             ("Who are Corla Denning's employees?", ("employer",)),
             ("Who is employed at Corla Denning?", ("employer",)),
             ("Who reports to Ives Brand?", _BOSSY),
             ("Who does Corla Denning work for?", None),
             ("Who is Corla Denning's employer?", None)]
    for q, want in extra:
        got = parse_extra251(q)
        got = got["rels"][:1] if got and want and len(want) == 1 else (
            got["rels"] if got else None)
        ok += got == want
        if got != want:
            print("FAIL", q, got, want)
    for q, want in cases:
        got = parse251(q)
        ok += got == want
        if got != want:
            print("FAIL", q, got, want)
    n = len(cases) + len(extra)
    print(f"selftest251 {ok}/{n}")
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(selftest251())
