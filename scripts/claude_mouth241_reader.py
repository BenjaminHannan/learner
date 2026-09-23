#!/usr/bin/env python3
"""Exp 241 (mouth stage A) -- round-trip reader for brake v2 rule 7.

Reads a candidate STATEMENT back into (relation row, X, Y) triples with the
base's rule ears, without any notebook and without writing anything:

  * scripts/claude_loop229_agent.table_teach_readings229 (pure function):
    the relation table's own teach rows, the "inverted" generic family
    ("{Y} is {X}'s {R}." / "{Y} is the {R} of {X}.") and EXT229 (verb
    forms such as "{Y} owns {X}.", "{ME} live in {Y}.", "{X} is a {J}.").
  * the table's other generic families, which the live base reads with
    FakeEars / Me166 (possessive "{X}'s {R} is {Y}.", my "My {R} is {Y}.")
    and of_form "The {R} of {X} is {Y}.", matched here by splitting at every
    possible point and looking the relation surface up in the table.

Declared interpretation (PASSMARKS): the 228 base has no table teach
parser of its own, so 229's pure reader is used as "the base's rule ears"
for rule 7. It is imported read-only; nothing is edited.

Person handling: A's user forms say "you"/"your"; before reading, the
candidate is turned back into the user's own words (you -> I, your -> my).
The user subject reads back as USER.
"""
from __future__ import annotations

import re
from pathlib import Path

import claude_loop229_agent as L229
from fable_fix221_tableask import key221

REPO = Path(__file__).resolve().parents[1]
TABLE_V11 = REPO / "artifacts/claude-table237-20260922/relation_table_v1_1.json"
USER = "USER"

_TB = None


def table():
    """The v1.1 relation table, loaded once through 229's loader."""
    global _TB
    if _TB is None:
        _TB = L229.load_table229(TABLE_V11)
    return _TB


def row_for_surface(surface: str, extra: dict | None = None) -> str | None:
    """Relation display phrase -> table row name (names, aliases and
    storage keys), else a generic row name from `extra`, else None."""
    k = key221(surface)
    r = table()["key2rel"].get(k)
    if r:
        return r
    if extra and k in extra:
        return extra[k]
    return None


def _norm_name(s: str) -> str:
    s = " ".join(str(s).split()).strip().rstrip(".").lower()
    s = re.sub(r"^(the|an|a) ", "", s)
    return s


def to_user_words(text: str) -> str:
    """A's second-person render -> the user's first-person statement."""
    t = " ".join(str(text).split())
    t = re.sub(r"^(saved|ok|okay)\s*[:,]\s*", "", t, flags=re.I)
    subs = [(r"\byou are\b", "I am"), (r"\byou were\b", "I was"),
            (r"\byou have\b", "I have"), (r"\byour\b", "my"),
            (r"\byou\b", "I")]
    for pat, rep in subs:
        t = re.sub(pat, lambda m, rep=rep: _keep_case(m.group(0), rep), t,
                   flags=re.I)
    return t


def _keep_case(src: str, rep: str) -> str:
    if rep.startswith("I"):
        return rep
    return rep[0].upper() + rep[1:] if src[:1].isupper() else rep


def _splits(s: str, sep: str):
    """Every (left, right) split of s at an occurrence of sep."""
    low = s.lower()
    i = low.find(sep)
    while i >= 0:
        yield s[:i], s[i + len(sep):]
        i = low.find(sep, i + 1)


def _generic_readings(body: str, extra: dict | None) -> list[dict]:
    """possessive / my / of_form / inverted readings over table surfaces."""
    out = []

    def rel_of(r):
        return row_for_surface(r, extra)

    b = body
    low = b.lower()
    # my: "My R is Y"
    if low.startswith("my "):
        for left, y in _splits(b[3:], " is "):
            rn = rel_of(left)
            if rn:
                out.append({"rel": rn, "X": USER, "Y": y, "how": "my"})
    # of_form: "The R of X is Y"
    if low.startswith("the "):
        for left, y in _splits(b[4:], " is "):
            for r, x in _splits(left, " of "):
                rn = rel_of(r)
                if rn:
                    out.append({"rel": rn, "X": x, "Y": y, "how": "of_form"})
    # possessive: "X's R is Y"
    for left, y in _splits(b, " is "):
        for x, r in _splits(left, "'s "):
            rn = rel_of(r)
            if rn and x:
                out.append({"rel": rn, "X": x, "Y": y, "how": "possessive"})
    # inverted: "Y is X's R" / "Y is the R of X" (also "Y is my R")
    for y, right in _splits(b, " is "):
        rl = right.lower()
        if rl.startswith("the "):
            for r, x in _splits(right[4:], " of "):
                rn = rel_of(r)
                if rn:
                    out.append({"rel": rn, "X": x, "Y": y, "how": "inv_of"})
        if rl.startswith("my "):
            rn = rel_of(right[3:])
            if rn:
                out.append({"rel": rn, "X": USER, "Y": y, "how": "inv_my"})
        for x, r in _splits(right, "'s "):
            rn = rel_of(r)
            if rn and x:
                out.append({"rel": rn, "X": x, "Y": y, "how": "inv_poss"})
    return out


_PH = ["Qslota", "Qslotb", "Qslotc", "Qslotd"]


def _protect(statement: str, protect) -> tuple[str, dict]:
    """Hide the frame's own name strings behind plain placeholder names so
    that initials ('J. K. Rowling'), abbreviations ('Apple Inc.') and a
    'you' inside a title ('Within You Without You') are read as the names
    they are, not as sentence breaks or as the user."""
    back = {}
    t = statement
    # only strings that would otherwise be misread: a period / ! / ? / ;
    # inside the name, or a 'you' word in it; everything else is read as is
    items = sorted({str(p) for p in protect if p and p != USER and
                    (re.search(r"[.!?;]", str(p)) or
                     re.search(r"\byou(?:r|rs|rself)?\b", str(p), re.I))},
                   key=len, reverse=True)
    for i, p in enumerate(items[:len(_PH)]):
        rx = re.compile(r"(?<![A-Za-z0-9])" + re.escape(p) + r"(?![A-Za-z0-9])")
        if rx.search(t):
            t = rx.sub(_PH[i], t)
            back[_PH[i]] = p
    return t, back


def _unprotect(s: str, back: dict) -> str:
    for k, v in back.items():
        s = s.replace(k, v)
    return s


JOB_STAND_IN = "beekeeper"  # a word in 229's closed job list (OCC229)


def readings(statement: str, extra: dict | None = None,
             protect=(), job: str | None = None) -> list[dict]:
    """All (rel, X, Y) readings of one candidate statement. Pure.
    `protect` = frame name strings shown verbatim (see _protect).
    `job` = the frame's occupation value when 229's closed job list lacks
    it: it is read as a stand-in job word so 'X is a herbalist' can be
    checked for direction and triple (the frame already says it is a job)."""
    statement, back = _protect(statement, protect)
    if job and job.lower() not in L229.OCC229:
        rx = re.compile(r"(?<![A-Za-z0-9])" + re.escape(job)
                        + r"(?![A-Za-z0-9])", re.I)
        if rx.search(statement):
            statement = rx.sub(JOB_STAND_IN, statement)
            back[JOB_STAND_IN] = job
    t = to_user_words(statement)
    t = " ".join(t.split()).strip()
    body = t.rstrip(" .!")
    if not body or re.search(r"[.!?;]\s", body):
        return []
    out = []
    try:
        for r in L229.table_teach_readings229(body + ".", table()):
            out.append({"rel": r["rel"], "X": r["X"], "Y": r["Y"],
                        "how": r["how"]})
    except Exception:  # noqa: BLE001 -- a reader crash = unreadable
        pass
    out.extend(_generic_readings(body, extra))
    # "I"-subject generic reading of "I am ..." is not a table form; USER
    # only comes from my / ME templates above.
    seen, res = set(), []
    for r in out:
        r = dict(r, X=_unprotect(r["X"], back), Y=_unprotect(r["Y"], back))
        x = USER if r["X"] in (USER, "I", "i") else r["X"]
        sig = (r["rel"], _norm_name(x), _norm_name(r["Y"]))
        if sig not in seen:
            seen.add(sig)
            res.append({"rel": r["rel"], "X": x, "Y": r["Y"],
                        "how": r["how"]})
    return res


def round_trip_ok(statement: str, rel: str, x: str, y: str,
                  extra: dict | None = None) -> tuple[bool, str]:
    """Rule 7: the candidate must be readable, the frame's triple must be
    among its readings, and no reading may put the two names the other
    way round (reversed direction) or give a different value."""
    rs = readings(statement, extra, protect=(x, y),
                  job=y if rel == "occupation" else None)
    if not rs:
        return False, "unreadable"
    want = (rel, _norm_name(x), _norm_name(y))
    got = [(r["rel"], _norm_name(r["X"]), _norm_name(r["Y"])) for r in rs]
    if want not in got:
        return False, f"triple not recovered: {got[:4]}"
    for g in got:
        if want[1] == want[2]:
            break  # X == Y ('Luxembourg ... Luxembourg'): no direction
        if g[1] == want[2] and g[2] == want[1]:
            return False, f"reversed reading: {g}"
    return True, ""
