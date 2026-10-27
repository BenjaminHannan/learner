#!/usr/bin/env python3
"""Exp 241b (mouth stage A v2) -- the say table v2 and the renderer.

241b changes (brief 241b a-e, g): say_kind column (name / common / number /
date / free); CONFLICT new value rendered as a value (article, capital for
kind 'name', particle exemption); BROKEN_CHAIN wording for any value type;
FORGOTTEN_ONE never makes the value a subject; a value's own leading
'The' is kept; an exact repeated list item is said once; AMBIGUOUS drops
'(E...)' codes when the full names differ (identical names -> no candidate,
the caller passes the line through and counts it). Brief g (optional) is
NOT done: part 1 ('Saved:' capital) and part 2 (possessive for s/x/z names)
both showed risk on the pilot (PASSMARKS). 241 text follows.


build:  python -B scripts/claude_mouth241b_say.py --build
        -> artifacts/claude-mouth241b-20260922/say_forms.json

One row per relation in relation_table_v1_1.json (150) plus a generic row
used for relation nouns the base shows that the table lacks. A row holds:
  affirm        verb forms "{S} lives in {V}." (kept only if the round-trip
                reader reads them back as (row, S, V) with two filler sets)
                followed by the always-available noun form "{NP} is {V}."
  user          the same for the user as subject ("you live in {V}.")
  abstain_missing / abstain_user   "I don't know where {S} lives." ...
  inverse       "{V} is the {R} of {S}." (138i reverse-lookup shape; 221's
                "worked out backwards" provenance does not occur in the base)
  yes / no / notknown   the 154d shapes (they must keep "is {V}")
  self          null: the notebook holds no facts about the assistant; the
                assistant's own replies are fixed acts (identity sheet).
  possessive_ok round trip of "{S}'s {R} is {V}." with the canonical fillers.

SCORER CONTRACT (PASSMARKS): every value-stating answer (ANSWER, LIST,
YES/NO, REVERSE, BROKEN_CHAIN) must keep "is {V}" / "are {V}" as its final
clause, because bench121 and rt143 read the answer after the last " is " /
" are ". Verb forms are therefore used for SAVED, CONFLICT, FORGOTTEN and
the missing-fact abstain, and for ANSWER only when the extracted value is
unchanged (occupation "Jon is a baker." -> "baker" after article removal).

Render API (pure; frame in, candidate texts out, preferred first):
  candidates(frame) -> list[str]
The caller (brake v2) picks the first candidate that passes.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_mouth241b_morph as M  # noqa: E402
import claude_mouth241b_reader as RD  # noqa: E402
from fable_fix221_tableask import key221  # noqa: E402

REPO = SCRIPTS.parent
ART = REPO / "artifacts/claude-mouth241b-20260922"
SAY_PATH = ART / "say_forms.json"

# ------------------------------------------------------------------ curated
# Hand-written verb forms. Direction is NOT trusted by eye: build() keeps a
# form only if the round-trip reader recovers (row, S, V) from it.
# {S} subject, {V} value, {a} a/an for V, {on} on/in for dates.
_BY = {"composer": "composed", "author": "wrote", "painter": "painted",
       "director": "directed", "founder": "founded", "inventor": "invented",
       "designer": "designed", "discoverer": "discovered",
       "architect": "built", "creator": "created",
       "developer": "developed", "performer": "performed"}

CURATED: dict[str, dict] = {
    "spouse": {"aff": ["{S} is married to {V}."],
               "user": ["you are married to {V}."],
               "wh": "who {S} is married to",
               "wh_user": "who you are married to"},
    "teacher": {"aff": ["{V} teaches {S}."], "wh": "who teaches {S}",
                "wh_user": "who teaches you"},
    "coach": {"aff": ["{V} coaches {S}."], "wh": "who coaches {S}",
              "wh_user": "who coaches you"},
    "owner": {"aff": ["{V} owns {S}."], "wh": "who owns {S}"},
    "employer": {"aff": ["{S} works at {V}."],
                 "user": ["you work at {V}."],
                 "wh": "where {S} works", "wh_user": "where you work"},
    "occupation": {"aff": ["{S} is {a} {V}.", "{S} works as {a} {V}."],
                   "user": ["you are {a} {V}.", "you work as {a} {V}."]},
    "school": {"aff": ["{S} goes to {V}."], "user": ["you go to {V}."],
               "wh": "what school {S} goes to",
               "wh_user": "what school you go to"},
    "educated_at": {"aff": ["{S} studied at {V}."],
                    "user": ["you studied at {V}."],
                    "wh": "where {S} studied",
                    "wh_user": "where you studied"},
    "city": {"aff": ["{S} lives in {V}."], "user": ["you live in {V}."],
             "wh": "where {S} lives", "wh_user": "where you live"},
    "hometown": {"aff": ["{S} is from {V}."], "user": ["you are from {V}."],
                 "wh": "where {S} is from", "wh_user": "where you are from"},
    "place_of_birth": {"aff": ["{S} was born in {V}."],
                       "user": ["you were born in {V}."],
                       "wh": "where {S} was born",
                       "wh_user": "where you were born"},
    "place_of_death": {"aff": ["{S} died in {V}."],
                       "wh": "where {S} died"},
    "date_of_birth": {"aff": ["{S} was born {on} {V}."],
                      "user": ["you were born {on} {V}."],
                      "wh": "when {S} was born",
                      "wh_user": "when you were born"},
    "date_of_death": {"aff": ["{S} died {on} {V}."], "wh": "when {S} died"},
    "age": {"aff": ["{S} is {V} years old."],
            "user": ["you are {V} years old."],
            "wh": "how old {S} is", "wh_user": "how old you are"},
    "language": {"aff": ["{S} speaks {V}."], "user": ["you speak {V}."],
                 "wh": "what language {S} speaks",
                 "wh_user": "what language you speak"},
    "headquarters_location": {"aff": ["{S} is based in {V}."],
                              "wh": "where {S} is based"},
    "country_of_citizenship": {"aff": ["{S} is a citizen of {V}."]},
    "manufacturer": {"aff": ["{S} is made by {V}."], "wh": "who makes {S}"},
    "hobby": {"aff": ["{S} likes {V}."]},
}
for _r, _v in _BY.items():
    CURATED[_r] = {"aff": ["{V} " + _v + " {S}."], "wh": f"who {_v} {{S}}"}

# Canonical fillers for the build-time round trip (fictional).
_FILL_V = {"person": ["Oren Pell", "Ivo"], "place": ["Kestrel Bay", "Porto"],
           "organization": ["Brindle Mill", "Acme"],
           "date": ["June 4", "1990"], "number": ["34", "7"],
           "literal": ["baker", "engineer"], "language": ["Veltish", "Oskan"],
           "work": ["The Long Tide", "Nocturne"]}
_FILL_S = ["Tamsin Vale", "Juniper Lane Books"]

_PREPS = {"by", "of", "in", "at", "to", "for", "on", "with", "from", "as",
          "and", "or", "the", "a", "an"}
_NOT_NAME_START = {"my", "your", "the", "a", "an", "his", "her", "our",
                   "their", "its", "this", "that"}
# 241b: a value/name starting with one of these lowercase particles is never
# re-cased (brief b)
PARTICLES = {"van", "von", "de", "da", "di", "du", "der", "la", "le", "bin",
             "al"}

# 241b say-table value-kind column (brief b): name / common / number /
# date / free. Only kind 'name' is ever capitalised (all-lowercase only).
SAY_KIND_BY_TABLE = {"person": "name", "place": "name",
                     "organization": "name", "language": "name",
                     "work": "name", "date": "date", "number": "number",
                     "literal": "common"}
SAY_KIND_BY_ROW = {"nickname": "name", "code": "free", "address": "free",
                   "phone_number": "free", "email": "free", "title": "free",
                   "age": "number"}


def say_kind_of(name: str, table_kind: str) -> str:
    if name in SAY_KIND_BY_ROW:
        return SAY_KIND_BY_ROW[name]
    return SAY_KIND_BY_TABLE.get(table_kind, "free")


_NOUN_RE = re.compile(r"^[a-z]+(?: [a-z]+){0,3}$")


# ------------------------------------------------------------------ helpers
def date_prep(v: str) -> str:
    """'on June 4' / 'on 4 June 1990' but 'in 1990' / 'in June 1990'."""
    toks = re.findall(r"[A-Za-z]+|\d+", str(v))
    has_day = any(t.isdigit() and len(t) <= 2 for t in toks)
    return "on" if has_day else "in"


def fill(tmpl: str, S: str, V: str) -> str:
    return (tmpl.replace("{S}", S).replace("{V}", V)
            .replace("{a}", M.a_an(V)).replace("{on}", date_prep(V)))


def cap_name(name: str) -> str:
    """Stored names echoed in the case the user typed: a name typed all in
    lower case is shown capitalised (238 LOWERCASE_NAME_ECHO)."""
    n = str(name)
    if n.split(" ")[0].lower() in _NOT_NAME_START:
        return n  # an ears misread ("my sister"), not a name: echo as is
    if n.split(" ")[0] in PARTICLES:
        return n  # 241b: 'van der berg' / 'de la cruz' stay as typed
    if n and n == n.lower() and re.search(r"[a-z]", n):
        return " ".join(w[:1].upper() + w[1:] for w in n.split(" "))
    return n


def generic_noun_ok(noun: str) -> bool:
    """A relation display the table lacks gets the generic row only if it
    looks like a plain noun phrase ('size', 'best mate'), never a verb or
    preposition phrase ('founded by')."""
    n = str(noun).strip()
    if not _NOUN_RE.match(n):
        return False
    words = n.split()
    if words[-1] in _PREPS or words[0] in _PREPS:
        return False
    if any(w.endswith("ed") or w.endswith("ing") for w in words):
        return False
    return True


# -------------------------------------------------------------- table build
def _row_record(r: dict, tb: dict) -> dict:
    name = r["name"]
    surfaces = RD.L229._surfaces(r)
    kind = r.get("value_kind") or "literal"
    cur = CURATED.get(name, {})
    fills_v = _FILL_V.get(kind, _FILL_V["literal"])
    dropped, aff_ok, user_ok = [], [], []
    for t in cur.get("aff", []):
        ok = True
        for S, V in zip(_FILL_S, fills_v):
            good, why = RD.round_trip_ok(fill(t, S, V), name, S, V)
            if not good:
                ok = False
                dropped.append({"form": t, "S": S, "V": V, "why": why})
                break
        if ok:
            aff_ok.append(t)
    for t in cur.get("user", []):
        V = fills_v[0]
        good, why = RD.round_trip_ok(fill(t, "", V), name, RD.USER, V)
        if good:
            user_ok.append(t)
        else:
            dropped.append({"form": t, "S": "USER", "V": V, "why": why})
    noun = surfaces[0]
    poss_ok, _ = RD.round_trip_ok(f"{_FILL_S[0]}'s {noun} is {fills_v[0]}.",
                                  name, _FILL_S[0], fills_v[0])
    of_ok, _ = RD.round_trip_ok(f"The {noun} of {_FILL_S[1]} is {fills_v[0]}.",
                                name, _FILL_S[1], fills_v[0])
    return {
        "name": name, "noun": noun, "plural": M.plural(noun),
        "surfaces": surfaces, "value_kind": kind,
        "say_kind": say_kind_of(name, kind),
        "cardinality": r.get("cardinality", "single"),
        "affirm": aff_ok + ["{NP} is {V}."],
        "user": user_ok + ["your {R} is {V}."],
        "abstain_missing": ("I don't know " + cur["wh"] + ".") if "wh" in cur
        else "I don't know " + _generic_wh(kind, "{NP}") + ".",
        "abstain_user": ("I don't know " + cur["wh_user"] + " yet.")
        if "wh_user" in cur
        else "I don't know " + _generic_wh(kind, "your {R}") + " yet.",
        "forgotten": "OK, I've forgotten " + (cur.get("wh") or
                                             _generic_wh(kind, "{NP}")) + ".",
        "forgotten_user": "OK, I've forgotten " + (
            cur.get("wh_user") or _generic_wh(kind, "your {R}")) + ".",
        "inverse": "{V} is the {R} of {S}.",
        "yes": "Yes, {NP} is {V}.", "no": "No, {NP} is {V}.",
        "notknown": "Not that I know of. I have {V} as {NP}.",
        "self": None,
        "possessive_ok": bool(poss_ok), "of_form_ok": bool(of_ok),
        "dropped": dropped,
    }


def _generic_wh(kind: str, np: str) -> str:
    if kind == "person":
        return f"who {np} is"
    if kind == "date":
        return f"when {np} is"
    return f"what {np} is"


def generic_row(noun: str) -> dict:
    return {
        "name": "_generic:" + key221(noun), "noun": noun,
        "plural": M.plural(noun), "surfaces": [noun], "value_kind": "literal",
        "say_kind": "free", "cardinality": "unknown", "affirm": ["{NP} is {V}."],
        "user": ["your {R} is {V}."],
        "abstain_missing": "I don't know {NP}.",
        "abstain_user": "I don't know your {R} yet.",
        "forgotten": "OK, I've forgotten {NP}.",
        "forgotten_user": "OK, I've forgotten your {R}.",
        "inverse": "{V} is the {R} of {S}.",
        "yes": "Yes, {NP} is {V}.", "no": "No, {NP} is {V}.",
        "notknown": "Not that I know of. I have {V} as {NP}.",
        "self": None, "possessive_ok": True, "of_form_ok": True,
        "dropped": [], "generic": True,
    }


def build() -> dict:
    tb = RD.table()
    data = json.loads(Path(RD.TABLE_V11).read_text(encoding="utf-8"))
    rows = {}
    for r in data["relations"]:
        rows[r["name"]] = _row_record(r, tb)
    out = {"version": "241b-A-2", "source_table": str(RD.TABLE_V11.relative_to(REPO)),
           "rows": rows,
           "generic_row_template": generic_row("{noun}"),
           "notes": ["generic rows are made at run time for a relation noun "
                     "the table lacks, only when generic_noun_ok(noun)",
                     "241b: say_kind column (name/common/number/date/free); "
                     "generic rows are 'free' (never re-cased)"]}
    return out


_SAY = None


def say_table() -> dict:
    global _SAY
    if _SAY is None:
        _SAY = json.loads(SAY_PATH.read_text(encoding="utf-8"))
    return _SAY


def row_for(noun: str) -> dict | None:
    """Say row for a relation display noun, else a generic row, else None."""
    rn = RD.row_for_surface(noun)
    if rn:
        return say_table()["rows"][rn]
    if generic_noun_ok(noun):
        return generic_row(noun)
    return None


def reader_extra(row: dict) -> dict | None:
    if row.get("generic"):
        return {key221(row["noun"]): row["name"]}
    return None


# ------------------------------------------------------------ noun phrases
def is_plural_noun(noun: str, row: dict) -> bool:
    n = noun.lower()
    return n.endswith("s") and any(s.lower() == n[:-1] for s in row["surfaces"])


def verbish(noun: str) -> bool:
    """A relation display that is a verb phrase ('educated at', 'date
    founded', 'position played on ...'), not a plain noun phrase."""
    ws = str(noun).lower().split()
    return bool(ws) and (ws[-1] in _PREPS or any(
        len(w) > 3 and w.endswith("ed") for w in ws))


def display_noun(noun: str, row: dict | None) -> str:
    """The noun A says: the display noun, or for a verb-phrase display the
    row's first plain-noun surface ('alma mater', 'founding date')."""
    if not row or not verbish(noun):
        return noun
    for sf in row.get("surfaces") or []:
        if not verbish(sf):
            return sf
    return noun


def plural_noun(noun: str, row: dict) -> str:
    return noun if is_plural_noun(noun, row) else M.plural(noun)


def np1(S: str, role: str, noun: str) -> str:
    """One-hop noun phrase: 'your city' / 'Mira's city' / 'the city of
    Silas' (names ending in s/x/z and 'the' names take the of form unless
    the noun already has 'of' in it)."""
    if role == "user":
        return f"your {noun}"
    S = cap_name(S)
    if must_of(S) or (prefer_of(S) and " of " not in noun):
        return f"the {noun} of {M.show_name(S)}"
    return f"{M.possessive(S)} {noun}"


def _plain_name(S: str) -> bool:
    """Every word a capitalised name word (or a lowercase particle), and
    no leading 'The': a person-style name such as 'Silas' or 'Ana van
    Dorn', not a phrase ('director of The Beatles') or a 'The' name."""
    ws = str(S).split()
    return bool(ws) and ws[0] != "The" and all(
        w[:1].isupper() or w in PARTICLES for w in ws)


def prefer_of(S: str) -> bool:
    """Of form ('the mother of Silas') for names ending in s/x/z and for
    'the' names -- 241's rule, kept. 241b brief g part 2 (possessive for
    s/x/z names) was tried and NOT adopted: on the suite lines it gave
    "Electronic Arts's", "General Motors's", "Gilded Mirrors's" (plural-
    looking names the mouth cannot tell from 'Silas'), so it is not
    risk-free (PASSMARKS). _plain_name is kept for the record only."""
    return M.needs_the(S) or M.ends_sxz(S)


# a name that reads as a plural ('Juniper Lane Books', 'the Netherlands')
# never takes "'s": always the of form (238 PLURAL_NAME_POSSESSIVE)
PLURAL_NAME_WORDS = {
    "Works", "Books", "Brothers", "Industries", "Systems", "Records",
    "Partners", "Labs", "Studios", "Games", "Sons", "Mills", "Gardens",
    "Islands", "Isles", "States", "Emirates", "Arms", "Springs", "Falls",
    # 241b: the scorer's plural-name list also has these
    "Netherlands", "Philippines", "Bahamas", "Maldives", "Beatles", "Stones",
}


def must_of(S: str) -> bool:
    ws = str(S).split()
    return M.needs_the(S) or (len(ws) > 1 and ws[-1] in PLURAL_NAME_WORDS)


def np_path(S: str, role: str, path: list[str]) -> str:
    """Multi-hop: two hops keep the stacked possessive ('Mira's mother's
    city'); three or more hops use 'the R of ...' outside two. A plural
    name ('Juniper Lane Books') uses the of form all the way."""
    if len(path) == 1:
        return np1(S, role, path[0])
    if role != "user" and must_of(cap_name(S)):
        inner = f"the {path[0]} of {M.show_name(cap_name(S))}"
        for r in path[1:]:
            inner = f"the {r} of {inner}"
        return inner
    head = "your" if role == "user" else M.possessive(cap_name(S))
    inner = f"{head} {path[0]}'s {path[1]}"
    for r in path[2:]:
        inner = f"the {r} of {inner}"
    return inner


def _poss_or_user(S, role):
    return "your" if role == "user" else M.possessive(cap_name(S))


def _say_kind(row: dict | None) -> str:
    if not row:
        return "free"
    return row.get("say_kind") or say_kind_of(row.get("name", ""),
                                              row.get("value_kind", ""))


def _entity_value(row: dict, v: str) -> str:
    """Values echo as stored; values of say kind 'name' typed all in lower
    case are shown capitalised (a display fix only; the particle exemption
    in cap_name applies). Place/org names take 'the' where English does."""
    if row.get("value_kind") in ("place", "organization"):
        return M.show_name(cap_name(v))  # 'lives in the United States'
    if _say_kind(row) == "name":
        return cap_name(v)
    v = str(v)
    art = ARTICLE_ROWS.get(row.get("name"))
    if art and v[:1].islower() and not re.match(r"(a|an|the)\b", v):
        return (M.with_article(v) if art == "a" else "the " + v)
    return v


_SING_S_END = ("ss", "us", "is", "ics", "ous", "ws")


def plural_looking(row: dict | None, v: str) -> bool:
    """241b (brief c): a value of say kind 'common' whose last word looks
    like a plural count noun ('noodles', 'story books'). Names, numbers,
    dates and free values are never plural here ('Kell Books is')."""
    if _say_kind(row) != "common":
        return False
    w = str(v).split()[-1] if str(v).split() else ""
    wl = w.lower()
    return (len(wl) > 3 and wl.isalpha() and wl.endswith("s")
            and not wl.endswith(_SING_S_END))


# literal values that are count nouns need an article ('Mira's pet is a
# hamster', 'Wren's instrument is the cello'); names and mass nouns do not
ARTICLE_ROWS = {"pet": "a", "toy": "a", "car": "a",
                "favorite_animal": "the", "instrument": "the"}


def conflict_value(row: dict | None, v: str) -> str:
    """241b (brief b): the CONFLICT new value as a value in running English
    ('the euphonium', 'an electric van', 'a tailor', 'Shethgean'). The
    stored value is never changed; only this text is."""
    if not row:
        return str(v)
    out = _entity_value(row, v)
    if (row.get("name") == "occupation" and out[:1].islower()
            and not re.match(r"(a|an|the)\b", out)):
        out = M.with_article(out)
    return out


def uniq(xs) -> list:
    """241b (brief d): an exact repeated list item is said once."""
    return list(dict.fromkeys(xs))


def _protected_the(c: str, keep) -> bool:
    """True when the clause starts with a frame string that itself begins
    with a capital 'The' (a title: 'The Quiet Tide')."""
    for k in keep or ():
        k = str(k)
        if k.startswith("The ") and c.startswith(k):
            return True
    return False


def _fill_row(t: str, row: dict, S: str, role: str, noun: str, V: str,
              np: str | None = None) -> str:
    np = np if np is not None else np1(S, role, noun)
    out = t.replace("{NP}", np).replace("{R}", noun)
    return fill(out, cap_name(S), V)


# ------------------------------------------------------------------ render
def affirm_clauses(fr: dict, V: str) -> list[str]:
    """Affirmative clauses (no prefix) for one (S, row, V), preferred first."""
    row = fr["_row"]
    S, role = fr["subject"]["text"], fr["subject"]["role"]
    noun = display_noun(fr["path"][-1], row)
    Vs = _entity_value(row, V)
    out = []
    if role == "user":
        for t in row["user"]:
            out.append(_fill_row(t, row, S, role, noun, Vs))
    else:
        for t in row["affirm"]:
            out.append(_fill_row(t, row, S, role, noun, Vs))
    return out


def candidates(fr: dict) -> list[str]:
    """All candidate texts for a frame, preferred first (already finished).
    fr["_row"] must be set by the caller (row_for)."""
    act = fr["act"]
    row = fr.get("_row")
    subj = fr.get("subject") or {}
    S, role = subj.get("text", ""), subj.get("role", "third")
    path = list(fr.get("path") or [])
    noun = display_noun(path[-1], row) if path else ""
    if path:
        # inner hops too: "Harborline's founder's spouse", not "founded by's"
        path = [display_noun(p, row_for(p)) for p in path[:-1]] + [noun]
    vals = [str(v) for v in fr.get("values", [])]
    out: list[str] = []

    def fin(t):
        return M.finish(t)

    if act == "ANSWER":
        V = _entity_value(row, vals[0]) if row else vals[0]
        if len(path) == 1:
            if row and row["name"] == "occupation":
                for c in affirm_clauses(fr, vals[0])[:1]:
                    out.append(fin(c))
            out.append(fin(f"{np1(S, role, noun)} is {V}."))
        else:
            out.append(fin(f"{np_path(S, role, path)} is {V}."))
    elif act == "ANSWER_LIST":
        Vs = uniq(_entity_value(row, v) for v in vals)
        pl = plural_noun(noun, row)
        if len(Vs) == 1:  # 241b: 'rowing and rowing' -> one item
            out.append(fin(f"{np_path(S, role, path)} is {Vs[0]}."))
        elif len(path) == 1:
            out.append(fin(f"{np1(S, role, pl)} are {M.join_list(Vs)}."))
        else:
            out.append(fin(f"{np_path(S, role, path[:-1] + [pl])} are "
                           f"{M.join_list(Vs)}."))
    elif act == "YESNO_YES":
        if row and row["name"] == "occupation" and len(path) == 1:
            for c in affirm_clauses(fr, vals[0])[:1]:  # 'Yes, Jon is a baker.'
                out.append(fin(f"Yes, {_lower_first(c, role)}"))
        out.append(fin(f"Yes, {np1(S, role, noun)} is "
                       f"{_entity_value(row, vals[0])}."))
    elif act == "YESNO_NO":
        Vs = uniq(_entity_value(row, v) for v in vals)
        if len(Vs) > 1:
            out.append(fin(f"No, {np1(S, role, plural_noun(noun, row))} are "
                           f"{M.join_list(Vs)}."))
        else:
            if row and row["name"] == "occupation" and len(path) == 1:
                for c in affirm_clauses(fr, vals[0])[:1]:
                    out.append(fin(f"No, {_lower_first(c, role)}"))
            out.append(fin(f"No, {np1(S, role, noun)} is {Vs[0]}."))
    elif act == "YESNO_NOTKNOWN":
        Vs = uniq(_entity_value(row, v) for v in vals)
        nn = plural_noun(noun, row) if len(Vs) > 1 else noun
        out.append(fin(f"Not that I know of. I have {M.join_list(Vs)} as "
                       f"{np1(S, role, nn)}."))
    elif act == "REVERSE":
        subs = uniq(cap_name(x) for x in fr.get("subjects", []))
        for nn in dict.fromkeys([noun, fr["path"][-1]]):
            # the scorers read 'the R of S' after ' is ': a verb-phrase
            # display ('educated at') may have to stay as it is
            # 241b (brief c): a plural-looking value agrees ('Noodles are
            # the favorite food of X'); the reader reads 'Y are the R of X'
            vb = "are" if plural_looking(row, vals[0]) else "is"
            out.append(fin(f"{_entity_value(row, vals[0])} {vb} the {nn} of "
                           f"{M.join_list([M.show_name(x) for x in subs])}."))
    elif act == "ABSTAIN_MISSING":
        np = np1(S, role, noun)
        if role == "user":
            t = row["abstain_user"]
            out.append(fin(_fill_row(t, row, S, role, noun, "", np)))
            out.append(fin(f"I don't know your {noun} yet."))
        else:
            out.append(fin(_fill_row(row["abstain_missing"], row, S, role,
                                     noun, "", np)))
            out.append(fin(f"I don't know {np}."))
    elif act == "UNKNOWN_ENTITY":
        out.append(fin(f"I don't know anyone called {cap_name(S)}."))
    elif act == "BROKEN_CHAIN":
        # 241b (brief a): right for any value type; the chain stops at V
        # because nothing is saved about V. 'about V' for a name value,
        # 'about that' for things, dates and numbers. Keeps the frozen
        # abstain anchor "i can only follow" (bench121 ABSTAIN_PHRASES,
        # rt143 'only follow', decline224) and adds no sessions152 clarify
        # bit (no "don't know"), so no scorer anchor verdict changes.
        Vs = _entity_value(row, vals[0]) if row else vals[0]
        about = Vs if _say_kind(row) == "name" else "that"
        tail = (f" I have nothing saved about {about}, so I can only follow "
                f"the chain this far.")
        if row and row["name"] == "occupation" and len(path) == 1:
            for c in affirm_clauses(fr, vals[0])[:1]:  # 'Jon is a tailor.'
                out.append(fin(c + tail))
        out.append(fin(f"{np_path(S, role, path)} is {Vs}.{tail}"))
    elif act == "AMBIGUOUS":
        # 241b (brief e): drop the '(E...)' codes when the full names
        # differ; identical names -> no candidate (caller passes through)
        names = ambiguous_names(fr.get("choices", []))
        if names is not None:
            out.append(fin(f"I know more than one {cap_name(S)}: "
                           f"{M.join_list([cap_name(n) for n in names])}. "
                           f"Which one do you mean?"))
    elif act == "SAVED":
        also = fr.get("also_have") or []
        # 241b (brief d): an exact repeat is said once, also across the
        # saved value and the 'also have' list
        v0 = _entity_value(row, vals[0]).casefold()
        also_v = [x for x in uniq(_entity_value(row, a) for a in also)
                  if x.casefold() != v0]
        tail = (f" (I also have {M.join_list(also_v)}.)" if also_v else "")
        for c in affirm_clauses(fr, vals[0]):
            out.append("Saved: " + _finish_after_colon(c) + tail)
    elif act == "DUPLICATE":
        out.append("I already have that.")
    elif act == "CONFLICT":
        old, new = fr["old_value"], fr["new_value"]
        # 241b (brief b): the new value is rendered as a value in running
        # English; the new 172b driver version (claude_fix172b241b_benchv3)
        # matches it case- and article-insensitively. Stored value unchanged.
        newv = conflict_value(row, new)
        # a VALUE that is a title keeps its 'The'; the subject is lowered
        # as in 241 ('the Beatles performed ...')
        keep = [_entity_value(row, old), newv] if row else []
        cl = affirm_clauses(fr, old)
        if _say_kind(row) == "number":
            cl = cl[-1:]  # 'Iththal's age is 6' (no units the user never gave)
        for c in cl:
            out.append(fin(f"My notes say {_lower_first(c, role, keep)} "
                           f"Do you want me to change it to {newv}?"))
        out.append(fin(f"I have {np1(S, role, noun)} as "
                       f"{_entity_value(row, old)}. Do you want me to change "
                       f"it to {newv}?"))
    elif act == "CONFIRM_RESULT":
        out.append("Okay, I left it as it was.")
    elif act == "FORGOTTEN":
        np = np1(S, role, noun)
        t = row["forgotten_user"] if role == "user" else row["forgotten"]
        out.append(fin(_fill_row(t, row, S, role, noun, "", np)))
        out.append(fin(f"OK, I've forgotten {np}."))
    elif act == "FORGOTTEN_ONE":
        # 241b (brief c): the value is never the subject of 'is' ('noodles
        # is ...' removed); a title keeps its own 'The'
        V = _entity_value(row, vals[0])
        keep = [V]
        clauses = [c for c in affirm_clauses(fr, vals[0])
                   if not c.endswith("is " + V + ".")]
        clauses.append(f"{np1(S, role, noun)} is {V}.")
        for c in clauses:
            out.append(fin(f"OK, I've forgotten that "
                           f"{_lower_first(c, role, keep)}"))
    elif act == "NOT_HAD":
        V = _entity_value(row, vals[0])
        if verbish(fr["path"][-1]):  # 'educated at': say the verb form
            for c in affirm_clauses(fr, vals[0])[:-1]:
                out.append(fin(f"I don't have a note that {_lower_first(c, role)[:-1]}"
                               f", so there was nothing to forget."))
        out.append(fin(f"I don't have {V} as {np1(S, role, noun)}, so there "
                       f"was nothing to forget."))
    elif act == "SELF_PEOPLE":
        out.append(fin(self_people_text(fr["count"], fr.get("names", []))))
    elif act == "SELF_FACTS":
        out.append(fin(self_facts_text(fr["count"], fr["count2"])))
    elif act == "SELF_SLEPT":
        n = fr["count"]
        out.append(fin("No, I haven't slept yet." if n == 0 else
                       f"Yes, I have slept {M.times_phrase(n)}."))
    elif act == "SELF_TURNS":
        n = fr["count"]
        out.append(fin("We haven't had any turns yet." if n == 0 else
                       f"We have had {M.count_phrase(n, 'turn')}."))
    elif act == "SELF_ANSWERED":
        n = fr["count"]
        out.append(fin("I haven't answered any questions yet." if n == 0 else
                       f"I have answered {M.count_phrase(n, 'question')}."))
    return out


_CODE_RE = re.compile(r"^(.+?) \((E\d+)\)$")


def ambiguous_names(choices) -> list | None:
    """Choice names without their '(E...)' codes when the full names all
    differ (case-insensitively), else None (identical names: pass the line
    through; owner = the ambiguity handler)."""
    names = []
    for c in choices or []:
        m = _CODE_RE.match(str(c))
        names.append(m.group(1) if m else str(c))
    if len({" ".join(n.lower().split()) for n in names}) != len(names):
        return None
    return names


def noun_is_row_noun(noun: str, row: dict) -> bool:
    return noun.lower() in [s.lower() for s in row["surfaces"]]


def _finish_after_colon(c: str) -> str:
    c = " ".join(c.split())
    if not c.endswith((".", "?", "!")):
        c += "."
    c = re.sub(r"(?<!\.)\.\.(?!\.)", ".", c)
    return c[:1].upper() + c[1:]  # 'Saved: You live in Lima.' 


def _lower_first(c: str, role: str, keep=()) -> str:
    """A clause placed mid-sentence: lower-case a leading 'You'/'Your'/'The'
    only (names keep their capitals; 241b: a frame string that itself
    starts with 'The', e.g. a title, keeps it)."""
    c = " ".join(c.split())
    if not c.endswith((".", "?", "!")):
        c += "."
    if _protected_the(c, keep):
        return c
    for w in ("You ", "Your ", "The "):
        if c.startswith(w):
            return w.lower() + c[len(w):]
    return c


def self_people_text(n: int, names: list[str]) -> str:
    """'I know N people: ...' with count agreement; the user shows as
    'you' (listed first); 0 -> a sentence without a list and without the
    clarify anchor 'don't know'."""
    n = int(n)
    # 241b: the base shows the user as 'USER' or (after its 173 rewrite)
    # as 'you' in place; both are the user: said 'you', listed first,
    # never capitalised mid-list (241 gave '..., Orkdra, You, Uvend ...')
    def is_user(x):
        return x == RD.USER or str(x).lower() == "you"
    shown = (["you"] * sum(1 for x in names if is_user(x))
             + [cap_name(x) for x in names if not is_user(x)])
    if n == 0:
        return "You haven't told me about anyone yet."
    return f"I know {M.count_phrase(n, 'person', 'people')}: {M.join_list(shown)}."


def self_facts_text(taught: int, web: int) -> str:
    t, w = int(taught), int(web)
    a = ("You haven't taught me any facts yet." if t == 0 else
         f"You have taught me {M.count_phrase(t, 'fact')}.")
    b = ("I hold no web rows." if w == 0 else
         f"I also hold {M.count_phrase(w, 'web row')}, which I do not "
         f"believe.")
    return a + " " + b


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    a = ap.parse_args(argv)
    if a.build:
        ART.mkdir(parents=True, exist_ok=True)
        data = build()
        SAY_PATH.write_text(json.dumps(data, indent=1, ensure_ascii=False)
                            + "\n", encoding="utf-8")
        rows = data["rows"]
        nverb = sum(1 for r in rows.values() if len(r["affirm"]) > 1)
        ndrop = sum(len(r["dropped"]) for r in rows.values())
        print(f"wrote {SAY_PATH.relative_to(REPO)}: {len(rows)} rows, "
              f"{nverb} with verb forms, {ndrop} forms dropped by round trip")
        for r in rows.values():
            for d in r["dropped"]:
                print("  dropped", r["name"], d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
