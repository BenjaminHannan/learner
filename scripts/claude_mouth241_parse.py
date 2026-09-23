#!/usr/bin/env python3
"""Exp 241 (mouth stage A) -- parse-back of the base's reply templates.

parse(line, records) -> frame | None

A line is FRAMED only when legacy(frame) reproduces it byte for byte, so the
parse can never silently lose content (this is also the M2(b) check). Any
other line is UNFRAMED and passes through unchanged.

Templates covered (the 228/138i base; sources in PASSMARKS):
  SAVED            "Saved: X's R is V." (+ " (I also have A and B.)")
  DUPLICATE        "I already have that."
  CONFLICT         "I have X's R as OLD. Do you want me to change it to NEW?"
  CONFIRM_RESULT   "Okay, I left it as it was."
  FORGOTTEN        "Forgotten: X's R."      FORGOTTEN_ONE "Forgotten: X's R V."
  NOT_HAD          "I don't have X's R V."
  ABSTAIN_MISSING  "I don't know X's R."  /  "I don't know your R yet."
  UNKNOWN_ENTITY   "I don't know anyone called X."
  BROKEN_CHAIN     "X's R is V, which is not someone I can look up."
  AMBIGUOUS        "I know more than one X: A (E1), B (E2). Which one do you mean?"
  YESNO_YES/NO     "Yes, X's R is V." / "No, X's R is W."
  YESNO_NOTKNOWN   "Not that I know of. I have W as X's R."
  REVERSE          "V is the R of A and B."
  ANSWER / LIST    "X's R1's R2 is V." / "Your R is A and B."
  SELF_PEOPLE      "I know N people: A, B."
  SELF_FACTS       "I know N facts you taught me. I also hold M web row, which I do not believe."
  SELF_SLEPT / SELF_TURNS / SELF_ANSWERED   (self99 count lines)
  NOTE prefix      "(I dropped my earlier question.) "
The user subject appears as "your"/"Your" (173 rewrite) or raw "USER".
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_mouth241_say as SAY  # noqa: E402

NOTE_DROPPED = "(I dropped my earlier question.) "
USER = "USER"
_REL_RE = re.compile(r"^[a-z][a-z0-9 \-]*$")
_CHOICE_RE = re.compile(r"(.+? \(E\d+\))(?:, |$)")


# ------------------------------------------------------------ legacy render
def _legacy_np(fr: dict, start: bool) -> str:
    s = fr["subject"]
    parts = list(fr["path"])
    if s["role"] == "user":
        if s.get("raw_user"):
            return "'s ".join([USER] + parts)
        head = "Your" if start else "your"
        return head + " " + "'s ".join(parts)
    return "'s ".join([s["text"]] + parts)


def _join_and(vals: list[str]) -> str:
    # 154b / 154d / 221 join: "A", "A and B", "A, B and C"
    if len(vals) <= 1:
        return "".join(vals)
    return ", ".join(vals[:-1]) + " and " + vals[-1]


def legacy(fr: dict) -> str:
    """The base's own template for a frame (used to verify the parse and to
    make the sweep's legacy_text)."""
    a = fr["act"]
    v = fr.get("values", [])
    pre = "".join(NOTE_DROPPED for n in fr.get("notes", [])
                  if n == "dropped_question")
    if a == "SAVED":
        t = f"Saved: {_legacy_np(fr, False)} is {v[0]}."
        if fr.get("also_have"):
            t += f" (I also have {_join_and(fr['also_have'])}.)"
    elif a == "DUPLICATE":
        t = "I already have that."
    elif a == "CONFLICT":
        t = (f"I have {_legacy_np(fr, False)} as {fr['old_value']}. "
             f"Do you want me to change it to {fr['new_value']}?")
    elif a == "CONFIRM_RESULT":
        t = "Okay, I left it as it was."
    elif a == "FORGOTTEN":
        t = f"Forgotten: {_legacy_np(fr, False)}."
    elif a == "FORGOTTEN_ONE":
        t = f"Forgotten: {_legacy_np(fr, False)} {v[0]}."
    elif a == "NOT_HAD":
        t = f"I don't have {_legacy_np(fr, False)} {v[0]}."
    elif a == "ABSTAIN_MISSING":
        if fr["subject"]["role"] == "user" and not fr["subject"].get("raw_user"):
            t = f"I don't know {_legacy_np(fr, False)} yet."
        else:
            t = f"I don't know {_legacy_np(fr, False)}."
    elif a == "UNKNOWN_ENTITY":
        t = f"I don't know anyone called {fr['subject']['text']}."
    elif a == "BROKEN_CHAIN":
        t = (f"{_legacy_np(fr, True)} is {v[0]}, which is not someone I can "
             f"look up.")
    elif a == "AMBIGUOUS":
        t = (f"I know more than one {fr['subject']['text']}: "
             f"{', '.join(fr['choices'])}. Which one do you mean?")
    elif a == "YESNO_YES":
        t = f"Yes, {_legacy_np(fr, False)} is {v[0]}."
    elif a == "YESNO_NO":
        t = f"No, {_legacy_np(fr, False)} is {_join_and(v)}."
    elif a == "YESNO_NOTKNOWN":
        t = f"Not that I know of. I have {_join_and(v)} as {_legacy_np(fr, False)}."
    elif a == "REVERSE":
        t = f"{v[0]} is the {fr['path'][-1]} of {' and '.join(fr['subjects'])}."
    elif a in ("ANSWER", "ANSWER_LIST"):
        t = f"{_legacy_np(fr, True)} is {_join_and(v)}."
    elif a == "SELF_PEOPLE":
        t = f"I know {fr['count']} people: {', '.join(fr['names'])}."
    elif a == "SELF_FACTS":
        t = (f"I know {fr['count']} facts you taught me. I also hold "
             f"{fr['count2']} web row, which I do not believe.")
    elif a == "SELF_SLEPT":
        t = ("No. I have slept 0 times." if fr["count"] == 0 else
             f"Yes. I have slept {fr['count']} times.")
    elif a == "SELF_TURNS":
        t = f"We have had {fr['count']} turns."
    elif a == "SELF_ANSWERED":
        t = f"I have answered {fr['count']} questions."
    else:
        raise ValueError(a)
    return pre + t


# ------------------------------------------------------------------ parsing
def _splits(s: str, sep: str):
    i = s.find(sep)
    while i >= 0:
        yield s[:i], s[i + len(sep):]
        i = s.find(sep, i + 1)


def parse_np(np: str, allow_multi: bool = True) -> list[dict]:
    """'X's R1's R2' / 'your R' / 'Your R' / "USER's R" -> candidate
    (subject, path) readings, most likely first."""
    out = []
    low = np
    for head, role, raw in (("your ", "user", False), ("Your ", "user", False),
                            ("USER's ", "user", True)):
        if low.startswith(head):
            path = low[len(head):].split("'s ")
            if all(_REL_RE.match(p) for p in path):
                out.append({"subject": {"text": USER, "role": role,
                                        **({"raw_user": True} if raw else {})},
                            "path": path})
    # third party: subject = text before the first "'s " whose remainder is
    # a chain of relation phrases
    for s, rest in _splits(np, "'s "):
        path = rest.split("'s ")
        if s and s != USER and all(_REL_RE.match(p) for p in path):
            if len(path) > 1 and not allow_multi:
                continue
            out.append({"subject": {"text": s, "role": "third"},
                        "path": path})
    return out


def _split_list(v: str) -> list[str]:
    if " and " not in v:
        return [v]
    head, last = v.rsplit(" and ", 1)
    return head.split(", ") + [last]


def _ok(fr: dict, line: str) -> dict | None:
    try:
        if legacy(fr) == line:
            return fr
    except Exception:  # noqa: BLE001
        return None
    return None


def _with_np(act, np, line, extra, allow_multi=True, start=False):
    for r in parse_np(np, allow_multi):
        fr = {"act": act, **r, **extra}
        if _ok(fr, line):
            return fr
    return None


def _answer_record_values(records, fr) -> list[str] | None:
    """List split from the structured answer record when it matches."""
    for rec in records or []:
        if rec.get("kind") != "answer" or rec.get("status") != "OK":
            continue
        f = rec.get("fields") or {}
        if list(rec.get("relations") or []) != list(fr["path"]):
            continue
        if not f.get("multi"):
            continue
        n = len(f.get("trail") or [])
        vals = _split_list(str(f.get("answer", "")))
        if n >= 2 and len(vals) == n:
            return vals
    return None


def parse(line: str, records: list | None = None) -> dict | None:
    """Frame for one reply line, or None (unframed)."""
    notes = []
    body = line
    while body.startswith(NOTE_DROPPED):
        notes.append("dropped_question")
        body = body[len(NOTE_DROPPED):]
    fr = _parse_body(body, records)
    if fr is None:
        return None
    fr["notes"] = notes
    fr["legacy_text"] = line
    if legacy(fr) != line:
        return None
    return fr


def _parse_body(line: str, records) -> dict | None:  # noqa: C901
    if line == "I already have that.":
        return {"act": "DUPLICATE"}
    if line == "Okay, I left it as it was.":
        return {"act": "CONFIRM_RESULT"}
    m = re.fullmatch(r"I know (\d+) people: (.*)\.", line)
    if m:
        n = int(m.group(1))
        names = [x for x in m.group(2).split(", ")] if m.group(2) else []
        if n == len(names):
            return {"act": "SELF_PEOPLE", "count": n, "names": names}
        return None
    m = re.fullmatch(r"I know (\d+) facts you taught me\. I also hold (\d+) "
                     r"web row, which I do not believe\.", line)
    if m:
        return {"act": "SELF_FACTS", "count": int(m.group(1)),
                "count2": int(m.group(2))}
    m = re.fullmatch(r"(?:No\. I have slept 0|Yes\. I have slept (\d+)) times\.",
                     line)
    if m:
        return {"act": "SELF_SLEPT", "count": int(m.group(1) or 0)}
    m = re.fullmatch(r"We have had (\d+) turns\.", line)
    if m:
        return {"act": "SELF_TURNS", "count": int(m.group(1))}
    m = re.fullmatch(r"I have answered (\d+) questions\.", line)
    if m:
        return {"act": "SELF_ANSWERED", "count": int(m.group(1))}

    m = re.fullmatch(r"Saved: (.+?) is (.+?)\.(?: \(I also have (.+)\.\))?",
                     line)
    if m:
        for np_, v in _np_value_splits(line[len("Saved: "):], m):
            also = _split_list(m.group(3)) if m.group(3) else []
            fr = _with_np("SAVED", np_, line,
                          {"values": [v], "also_have": also}, False)
            if fr:
                return fr
        return None
    m = re.fullmatch(r"I have (.+) as (.+)\. Do you want me to change it to "
                     r"(.+)\?", line)
    if m:
        for np_, old in _splits_all(m.group(1) + " as " + m.group(2), " as "):
            fr = _with_np("CONFLICT", np_, line,
                          {"old_value": old, "new_value": m.group(3)}, False)
            if fr:
                return fr
        return None
    m = re.fullmatch(r"Forgotten: (.+)\.", line)
    if m:
        body = m.group(1)
        whole = _with_np("FORGOTTEN", body, line, {"values": []}, False)
        wrow = SAY.row_for(whole["path"][-1]) if whole else None
        if wrow and not wrow.get("generic"):
            return whole
        one = _best_split("FORGOTTEN_ONE", body, line)
        orow = SAY.row_for(one["path"][-1]) if one else None
        if orow and not orow.get("generic"):
            return one  # 'grandson Ivo' = table row + value
        return whole if wrow else one
    m = re.fullmatch(r"I don't have (.+)\.", line)
    if m:
        return _best_split("NOT_HAD", m.group(1), line)
    m = re.fullmatch(r"I don't know anyone called (.+)\.", line)
    if m:
        return {"act": "UNKNOWN_ENTITY",
                "subject": {"text": m.group(1), "role": "third"}, "path": []}
    m = re.fullmatch(r"I don't know (.+?)( yet)?\.", line)
    if m:
        return _with_np("ABSTAIN_MISSING", m.group(1), line, {"values": []},
                        False)
    m = re.fullmatch(r"(.+) is (.+), which is not someone I can look up\.", line)
    if m:
        for np_, v in _splits_all(line[:-len(", which is not someone I can "
                                             "look up.")], " is "):
            fr = _with_np("BROKEN_CHAIN", np_, line, {"values": [v]})
            if fr:
                return fr
        return None
    m = re.fullmatch(r"I know more than one (.+?): (.+)\. Which one do you "
                     r"mean\?", line)
    if m:
        ch = _CHOICE_RE.findall(m.group(2))
        return {"act": "AMBIGUOUS",
                "subject": {"text": m.group(1), "role": "third"},
                "path": [], "choices": ch}
    m = re.fullmatch(r"(Yes|No), (.+)\.", line)
    if m:
        act = "YESNO_YES" if m.group(1) == "Yes" else "YESNO_NO"
        for np_, v in _splits_all(m.group(2), " is "):
            vals = [v] if act == "YESNO_YES" else _split_list(v)
            fr = _with_np(act, np_, line, {"values": vals}, False)
            if fr:
                return fr
        return None
    m = re.fullmatch(r"Not that I know of\. I have (.+)\.", line)
    if m:
        for v, np_ in _splits_all(m.group(1), " as "):
            fr = _with_np("YESNO_NOTKNOWN", np_, line,
                          {"values": _split_list(v)}, False)
            if fr:
                return fr
        return None
    # ANSWER / ANSWER_LIST (possessive left side)
    body = line[:-1] if line.endswith(".") else None
    if body:
        for np_, v in _splits_all(body, " is "):
            for r in parse_np(np_):
                fr = {"act": "ANSWER", **r, "values": [v]}
                if not _ok(fr, line):
                    continue
                vals = _answer_record_values(records, fr)
                if vals:
                    fr["act"], fr["values"] = "ANSWER_LIST", vals
                return fr
    best, key = None, None
    for v, rest in _splits_all(line[:-1] if line.endswith(".") else line,
                               " is the "):
        for noun, subs in _splits_all(rest, " of "):
            if not re.fullmatch(r"[a-z][a-z ]*", noun):
                continue
            fr = {"act": "REVERSE", "subject": {"text": "", "role": "third"},
                  "path": [noun], "values": [v],
                  "subjects": subs.split(" and ")}
            if not _ok(fr, line):
                continue
            row = SAY.row_for(noun)
            k = (1 if row and not row.get("generic") else 0, len(noun))
            if key is None or k > key:
                best, key = fr, k
    return best


def _best_split(act: str, body: str, line: str) -> dict | None:
    """'NP V' with no separator word: every split is tried; a table row
    beats a generic row, then the longest relation noun wins ('date
    founded' over 'date' + 'founded ...')."""
    best, key = None, None
    for np_, v in _splits_all(body, " "):
        fr = _with_np(act, np_, line, {"values": [v]}, False)
        if not fr:
            continue
        row = SAY.row_for(fr["path"][-1])
        if not row:
            continue
        k = (0 if row.get("generic") else 1, len(fr["path"][-1]))
        if key is None or k > key:
            best, key = fr, k
    return best


def _splits_all(s: str, sep: str):
    return list(_splits(s, sep))


def _np_value_splits(body: str, m):
    """(np, value) splits of 'NP is V.' inside a SAVED line."""
    core = body
    if m.group(3):
        core = body[:body.rfind(" (I also have ")]
    core = core[:-1] if core.endswith(".") else core
    return _splits_all(core, " is ")
