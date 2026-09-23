#!/usr/bin/env python3
"""Exp 241b M1 sweep generator (new sealed seed SEED241B).

241b changes vs 241's generator (nothing else): the seed (SEED241B), and
fillers are drawn WITHOUT replacement inside each reply (no value, subject,
or list item repeats inside one reply; 241's repeated list items came from
the generator). Identical-name AMBIGUOUS lines are not generated: the 228
base cannot make two entities with the same full name (builder probe,
PASSMARKS), so the identical-name passthrough is unit-tested only. A
drawn name is never one of RESERVED_WORDS ('User', 'None', ...).

241 text follows.

Every act in 240 table 1.3 x every relation row the act can take x 4 tricky
filler classes, stratified to about 1,200 replies. Fillers are fictional
names drawn from a syllable pool made with SEED241B (sealed; the builder
never tunes on the drawn pool). Each frame is written as the BASE's legacy
line (parse.legacy), then sent through the real 241b path
(claude_loop241b_agent.render_line: parse-back -> say candidates -> brake v2),
so the sweep measures exactly what a user would see.

Filler classes:
  sxz    subject name ends in s/x/z (possessive / of-form trap)
  vowel  value starts with a vowel sound (a/an trap), vowel-initial names
  multi  multi-word subject and value names
  lower  subject and value typed in lower case (echo / sentence-case trap)
The user subject ("your ...") is drawn in about a quarter of the non-sxz
cases for the acts that take it.

Outputs (artifacts/claude-mouth241b-20260922/):
  sweep.jsonl         {id, act, text}         -> the grader (nothing else)
  sweep-frames.jsonl  {id, act, cls, frame, legacy_text, records, route,
                       why, ms}               -> M2(a) / M5 only
Run: uv ... python -B scripts/claude_mouth241b_sweep.py [--dry]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_mouth241b_parse as P  # noqa: E402
import claude_mouth241b_say as S  # noqa: E402

REPO = SCRIPTS.parent
ART = REPO / "artifacts/claude-mouth241b-20260922"
SEED241B = 241_0922_83  # sealed (241b; 241 used 241_0922_07)
CLASSES = ("sxz", "vowel", "multi", "lower")
ROW_ACT_N = 80
FIXED_N = {"DUPLICATE": 4, "CONFIRM_RESULT": 4, "UNKNOWN_ENTITY": 30,
           "AMBIGUOUS": 30, "SELF_PEOPLE": 40, "SELF_FACTS": 20,
           "SELF_SLEPT": 12, "SELF_TURNS": 12, "SELF_ANSWERED": 12}
ROW_ACTS = ("SAVED", "CONFLICT", "FORGOTTEN", "FORGOTTEN_ONE", "NOT_HAD",
            "ABSTAIN_MISSING", "BROKEN_CHAIN", "YESNO_YES", "YESNO_NO",
            "YESNO_NOTKNOWN", "REVERSE", "ANSWER", "ANSWER_LIST")
USER_ACTS = set(ROW_ACTS) - {"REVERSE"}
MULTIHOP_ACTS = {"ANSWER", "ANSWER_LIST", "BROKEN_CHAIN"}
LIST_ACTS = {"ANSWER_LIST"}             # multi-cardinality rows only
SINGLE_ACTS = {"CONFLICT"}              # single-cardinality rows only
# relation nouns the base uses that the table lacks (generic say rows)
GENERIC_NOUNS = ("best mate", "shoe size", "piano teacher", "landlady")
HOP_NOUNS = ("mother", "boss", "friend", "sister", "coach", "owner")

# ------------------------------------------------------------ name pool
_ON = ["b", "d", "f", "g", "h", "k", "l", "m", "n", "p", "r", "s", "t", "v",
       "w", "br", "dr", "gr", "kr", "tr", "st", "th", "sh"]
_NU = ["a", "e", "i", "o", "u", "ai", "ea", "io"]
_CO = ["", "", "n", "l", "r", "m", "th", "nd", "rk", "ll"]
_V0 = ["A", "E", "I", "O", "U"]
_SXZ = ["s", "x", "z", "as", "is", "ez", "ix", "us", "os"]
_PLACE_SUF = ["ford", "mere", "haven", "wick", "holm", "stead", "port"]
_ORG_SUF = ["Mill", "Guild", "Press", "Works", "Books", "Foundry", "Hall"]
_LANG_SUF = ["ish", "ic", "an", "ese"]
_WORK_A = ["Long", "Silver", "Quiet", "Hollow", "Amber", "Iron", "Evening"]
_WORK_N = ["Tide", "Orchard", "Lantern", "Harbour", "Meadow", "Ember"]
_MONTHS = ["January", "March", "April", "June", "August", "October"]
_LIT = {
    "occupation": (["baker", "tailor", "potter", "welder", "courier"],
                   ["engineer", "usher", "umpire", "architect", "herbalist",
                    "optician", "honest broker"]),
    "hobby": (["knitting", "rowing", "chess"], ["archery", "origami",
                                                 "embroidery"]),
    "pet": (["hamster", "parrot"], ["iguana", "otter"]),
    "sport": (["tennis", "rugby"], ["ice hockey", "archery"]),
    "instrument": (["cello", "flute"], ["oboe", "euphonium", "accordion"]),
    "favorite_color": (["green", "teal"], ["orange", "indigo", "amber"]),
    "color": (["green", "grey"], ["orange", "ochre"]),
    "favorite_food": (["noodles", "pie"], ["onion soup", "apricots"]),
    "favorite_animal": (["heron", "fox"], ["owl", "elk"]),
    "mood": (["cheerful", "tired"], ["upbeat", "anxious"]),
    "major": (["biology", "history"], ["economics", "art history"]),
    "genre": (["folk", "jazz"], ["opera", "electronica"]),
}
_LIT.update({
    "nickname": (["Bramble", "Pip"], ["Ace", "Echo"]),
    "title": (["Doctor", "Captain"], ["Elder", "Archivist"]),
    "code": (["K7", "B12"], ["X9", "A4"]),
    "address": (["12 Brindle Road", "4 Kestrel Lane"],
                ["8 Oriel Street", "11 Elm Row"]),
    "phone_number": (["555 0142", "555 0199"], ["555 0181", "555 0118"]),
    "email": (["pip@example.org", "tam@example.org"],
              ["ada@example.org", "echo@example.org"]),
    "car": (["red hatchback", "green van"], ["old estate car", "electric van"]),
    "toy": (["kite", "yo-yo"], ["action figure", "abacus"]),
    "religion_or_worldview": (["Quaker", "Buddhist"], ["agnostic", "atheist"]),
    "position_played_on_team_speciality": (["goalkeeper", "striker"],
                                           ["outside centre", "infielder"]),
    "training_data": (["simple English", "story books"],
                      ["English lessons", "encyclopedia pages"]),
})
_LIT_DEFAULT = (["Rowan", "Tarn"], ["Ember", "Ilex"])


# 241b: a drawn name never equals a role / machine word (the dev pilot drew
# "User", which reads as the user or as a placeholder, not as a name)
RESERVED_WORDS = {"user", "you", "your", "me", "none", "null", "nobody",
                  "someone", "anyone", "everyone", "yes", "okay", "the",
                  "and", "saved"}


class Pool:
    def __init__(self, seed: int):
        self.r = random.Random(seed)
        self.used = set()

    def _syl(self, onset=True):
        return ((self.r.choice(_ON) if onset else "") + self.r.choice(_NU)
                + self.r.choice(_CO))

    def _fresh(self, fn):
        for _ in range(200):
            n = fn()
            if (n.lower() not in self.used and len(n) >= 3
                    and n.lower() not in RESERVED_WORDS):
                self.used.add(n.lower())
                return n
        raise RuntimeError("pool exhausted")

    def word(self, vowel=False, sxz=False):
        def mk():
            w = (self.r.choice(_V0).lower() + self.r.choice(_CO)
                 if vowel else self._syl())
            w += self._syl()
            if sxz:
                w = w.rstrip("sxz") + self.r.choice(_SXZ)
            return w[:1].upper() + w[1:]
        return self._fresh(mk)

    def person(self, cls, multi_ok=True):
        if cls == "sxz":
            return (self.word(sxz=True) if self.r.random() < 0.6 else
                    self.word() + " " + self.word(sxz=True))
        if cls == "multi" and multi_ok:
            return " ".join(self.word() for _ in range(self.r.choice((2, 3))))
        if cls == "vowel":
            return self.word(vowel=True)
        return self.word()

    def entity(self, kind, cls, rowname=""):
        r = self.r
        vow = cls == "vowel"
        if kind == "person":
            return (self.word(vowel=True) if vow else
                    self.person("multi" if cls == "multi" else "plain"))
        if kind == "place":
            base = self.word(vowel=vow).lower()
            n = (base + r.choice(_PLACE_SUF)).capitalize()
            return n + " " + self.word() if cls == "multi" else n
        if kind == "organization":
            return self.word(vowel=vow) + " " + r.choice(_ORG_SUF)
        if kind == "language":
            return self.word(vowel=vow).rstrip("aeiou") + r.choice(_LANG_SUF)
        if kind == "work":
            return "The " + r.choice(_WORK_A) + " " + r.choice(_WORK_N)
        if kind == "date":
            return r.choice([f"{r.choice(_MONTHS)} {r.randint(1, 28)}",
                             f"{r.randint(1, 28)} {r.choice(_MONTHS)} "
                             f"{r.randint(1950, 2010)}",
                             str(r.randint(1900, 2020)),
                             f"{r.choice(_MONTHS)} {r.randint(1950, 2010)}"])
        if kind == "number":
            return str(r.choice([8, 11, 18, 80, 34, 6, 72]) if vow
                       else r.randint(2, 99))
        cons, vows = _LIT.get(rowname, _LIT_DEFAULT)
        return r.choice(vows if vow else cons)


# ------------------------------------------------------------ frames
def _rows():
    tbl = S.say_table()["rows"]
    rows = [dict(r) for r in tbl.values()]
    for n in GENERIC_NOUNS:
        rows.append(S.generic_row(n))
    return rows


def _lower(x: str) -> str:
    return x.lower()


def make_frame(act, row, cls, pool: Pool, r: random.Random):
    kind = row["value_kind"]
    noun = row["noun"]
    user = (cls != "sxz" and act in USER_ACTS and r.random() < 0.25)
    if user:
        subj = {"text": P.USER, "role": "user"}
        if act == "ABSTAIN_MISSING" and r.random() < 0.3:
            subj["raw_user"] = True
    else:
        subj = {"text": pool.person(cls), "role": "third"}
        if cls == "sxz" and r.random() < 0.3:  # plural-looking org name
            subj["text"] = pool.word() + " " + r.choice(("Works", "Books"))
    path = [noun]
    if act in MULTIHOP_ACTS and r.random() < 0.35:
        path = [r.choice(HOP_NOUNS) for _ in range(r.choice((1, 2)))] + [noun]

    drawn = {subj["text"].lower()}

    def val():
        """One filler, never one already drawn in this reply (241b)."""
        for tries in range(60):
            # after 30 tries, draw from the other half of a small list
            c = cls if tries < 30 else (
                "plain" if cls == "vowel" else "vowel")
            v = pool.entity(kind, c, row["name"])
            v = _lower(v) if cls == "lower" and kind in (
                "person", "place", "organization") else v
            if v.lower() not in drawn:
                drawn.add(v.lower())
                return v
        return None

    def vals(k):
        out = [val() for _ in range(k)]
        return [v for v in out if v is not None]

    if cls == "lower" and subj["role"] == "third":
        subj["text"] = subj["text"].lower()
    fr = {"act": act, "subject": subj, "path": path, "notes": []}
    if r.random() < 0.04:
        fr["notes"] = ["dropped_question"]
    if act in ("SAVED",):
        fr["values"] = [val()]
        fr["also_have"] = (vals(r.choice((1, 2)))
                           if row["cardinality"] == "multi"
                           and r.random() < 0.4 else [])
    elif act == "CONFLICT":
        fr["old_value"] = val()
        fr["new_value"] = val()
    elif act in ("FORGOTTEN", "ABSTAIN_MISSING"):
        fr["values"] = []
    elif act in ("FORGOTTEN_ONE", "NOT_HAD", "YESNO_YES", "BROKEN_CHAIN",
                 "ANSWER"):
        fr["values"] = [val()]
    elif act in ("YESNO_NO", "YESNO_NOTKNOWN"):
        k = (r.choice((1, 2, 3)) if row["cardinality"] != "single" else 1)
        fr["values"] = vals(k)
    elif act == "ANSWER_LIST":
        fr["values"] = vals(r.choice((2, 2, 3, 4)))
    elif act == "REVERSE":
        fr["subject"] = {"text": "", "role": "third"}
        fr["path"] = [noun]
        fr["values"] = [val()]
        fr["subjects"] = [pool.person(cls) for _ in range(r.choice((1, 1, 2)))]
        # (pool names are unique across the whole sweep: no repeats)
        if cls == "lower":
            fr["subjects"] = [x.lower() for x in fr["subjects"]]
    return fr


def fixed_frame(act, i, pool: Pool, r: random.Random):
    cls = CLASSES[i % 4]
    if act == "DUPLICATE":
        return {"act": act}, cls
    if act == "CONFIRM_RESULT":
        return {"act": act}, cls
    if act == "UNKNOWN_ENTITY":
        n = pool.person(cls)
        return {"act": act, "subject": {"text": n.lower() if cls == "lower"
                                        else n, "role": "third"},
                "path": []}, cls
    if act == "AMBIGUOUS":
        n = pool.word(sxz=cls == "sxz", vowel=cls == "vowel")
        k = r.choice((2, 2, 3))
        ch = [f"{n} {pool.word()} (E{r.randint(1, 9999):04d})"
              for _ in range(k)]
        return {"act": act, "subject": {"text": n, "role": "third"},
                "path": [], "choices": ch}, cls
    if act == "SELF_PEOPLE":
        n = r.choice((0, 1, 1, 2, 3, 4, 7, 12))
        names = [pool.person(cls) for _ in range(n)]
        if n and r.random() < 0.5:   # director case: USER in the list
            names[r.randrange(n)] = "USER"
        return {"act": act, "count": n, "names": names}, cls
    if act == "SELF_FACTS":
        return {"act": act, "count": r.choice((0, 1, 2, 5, 9, 14, 40)),
                "count2": r.choice((0, 0, 1, 3, 12))}, cls
    return {"act": act, "count": r.choice((0, 1, 2, 3, 7, 9, 10, 25))}, cls


def records_for(fr):
    if fr["act"] != "ANSWER_LIST":
        return []
    return [{"kind": "answer", "status": "OK", "relations": list(fr["path"]),
             "fields": {"multi": True, "trail": list(range(len(fr["values"]))),
                        "answer": P._join_and(fr["values"])}}]


def plan(r: random.Random):
    """Stratified (act, row, cls) picks: 80 per row act, 20 per class,
    rows chosen least-used-first so every row appears across the sweep."""
    rows = _rows()
    use = Counter()
    picks = []
    for act in ROW_ACTS:
        ok = [x for x in rows
              if not (act in LIST_ACTS and x["cardinality"] != "multi")
              and not (act in SINGLE_ACTS and x["cardinality"] == "multi")]
        for cls in CLASSES:
            for _ in range(ROW_ACT_N // 4):
                r.shuffle(ok)
                ok.sort(key=lambda x: use[x["name"]])
                row = ok[0]
                use[row["name"]] += 1
                picks.append((act, row, cls))
    return picks, use, rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true",
                    help="print counts only, write nothing")
    ap.add_argument("--out", default=str(ART))
    ap.add_argument("--pilot-seed", type=int, default=None,
                    help="pilot only (never the sealed seed); the registered "
                         "sweep uses SEED241B")
    a = ap.parse_args(argv)
    seed = SEED241B if a.pilot_seed is None else a.pilot_seed
    import claude_loop241b_agent as A241B  # real render path

    r = random.Random(seed)
    pool = Pool(seed + 1)
    picks, use, rows = plan(r)
    items = []
    for act, row, cls in picks:
        items.append((make_frame(act, row, cls, pool, r), cls))
    for act, n in FIXED_N.items():
        for i in range(n):
            items.append(fixed_frame(act, i, pool, r))
    # a handful of the director's exact case, always present
    items.append(({"act": "SELF_PEOPLE", "count": 1, "names": ["USER"]},
                  "director"))
    sweep, frames = [], []
    for k, (fr, cls) in enumerate(items):
        leg = P.legacy(fr)
        recs = records_for(fr)
        res = A241B.render_line(leg, recs, [])
        sid = f"s{k + 1:04d}"
        sweep.append({"id": sid, "act": fr["act"], "text": res["text"]})
        frames.append({"id": sid, "act": fr["act"], "cls": cls,
                       "gen_frame": fr, "frame": res.get("frame"),
                       "legacy_text": leg, "records": recs,
                       "route": res["route"], "why": res.get("why"),
                       "ms": res["ms"]})
    missing = [x["name"] for x in rows if use[x["name"]] == 0]
    routes = Counter(f["route"] for f in frames)
    by_act = Counter(f["act"] for f in frames)
    print(f"items {len(sweep)}; routes {dict(routes)}; rows unused "
          f"{len(missing)}")
    print("by act", dict(by_act))
    nonA = defaultdict(list)
    for f in frames:
        if f["route"] != "A":
            nonA[(f["act"], f["route"], f.get("why"))].append(f["legacy_text"])
    for k, v in sorted(nonA.items()):
        print("  non-A", k, len(v), v[:2])
    if not a.dry:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "sweep.jsonl", "w", encoding="utf-8") as fh:
            for s in sweep:
                fh.write(json.dumps(s, ensure_ascii=False) + "\n")
        with open(out / "sweep-frames.jsonl", "w", encoding="utf-8") as fh:
            for f in frames:
                fh.write(json.dumps(f, ensure_ascii=False) + "\n")
        print("wrote", out / "sweep.jsonl", "and sweep-frames.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
