#!/usr/bin/env python3
"""Exp 235b -- the dev set used ONLY to choose tau (no training happens in 235b).

= 900 rows sampled (seed 2352) from the 235 dev split (whole held-out templates)
+ new risk families written here (own wordings, never seen in training):
  R1  pronoun reference across clauses (a named third person, often the speaker's relative)
  R2  statement-shaped questions -> NONE (tag questions, rising "so ...?", "??", no-"?" chat)
  R2s statements that contain a question word but state a fact -> TEACH
  R3  the verb decides the relation (teaches/coaches/lectures at -> employer;
      studies/enrolled at -> school, educated_at also accepted)
Gold lines use the 235 format; a relation written "a/b" accepts either.

python claude_smolear235b_devdata.py --out artifacts/claude-smolear235b-20260922/dev/dev235b.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_data as D  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE_DEV = ROOT / "artifacts/claude-smolear235-20260922/data/dev.jsonl"

FEM = [("sister", "sister"), ("wife", "wife"), ("mum", "mother"), ("aunt", "aunt"),
       ("daughter", "daughter"), ("grandma", "grandmother")]
MASC = [("brother", "brother"), ("husband", "husband"), ("dad", "father"), ("uncle", "uncle"),
        ("son", "son"), ("grandpa", "grandfather")]
NEUT = [("cousin", "cousin"), ("best friend", "best_friend"), ("boss", "boss"),
        ("neighbour", "neighbour"), ("colleague", "colleague"), ("friend", "friend")]
MONTHS = ["January", "March", "April", "June", "August", "October", "November"]
VENUES = ["bus stop", "library", "farmers market", "gym", "school gate", "pub quiz"]


def vp(r, nm, exclude=()):
    """third-person verb phrase -> (text, relation, value)."""
    opts = [("city", lambda: nm.place(), "lives in {v}"),
            ("employer", lambda: nm.org(), "works at {v}"),
            ("occupation", lambda: r.choice(D.OCC), "works as {a} {v}"),
            ("language", lambda: r.choice(D.LANG), "speaks {v}"),
            ("place_of_birth", lambda: nm.place(), "was born in {v}"),
            ("hometown", lambda: nm.place(), "comes from {v}")]
    opts = [o for o in opts if o[0] not in exclude]
    rel, val, pat = r.choice(opts)
    v = val()
    a = "an" if v[0].lower() in "aeiou" else "a"
    return pat.format(v=v, a=a), rel, v


def pick_rel(r):
    k = r.random()
    if k < 0.4:
        w, rel = r.choice(FEM)
        return w, rel, "she"
    if k < 0.8:
        w, rel = r.choice(MASC)
        return w, rel, "he"
    w, rel = r.choice(NEUT)
    return w, rel, r.choice(["she", "he"])


def T(s, rel, v):
    return f"TEACH | {s} | {rel} | {v}"


def r1(r, nm):
    k = r.randrange(8)
    n = nm.first() if r.random() < 0.6 else nm.person()
    relw, rel, pro = pick_rel(r)
    text, vrel, v = vp(r, nm)
    if k == 0:
        return f"My {relw} is {n}, and {pro} {text}.", [T("my", rel, n), T(n, vrel, v)], "r1_my_and"
    if k == 1:
        return f"{n} is my {relw} — {pro} {text}.", [T("my", rel, n), T(n, vrel, v)], "r1_is_my"
    if k == 2:
        art = "an" if relw[0] in "aeiou" else "a"
        return f"I have {art} {relw} called {n}; {pro} {text}.", [T("I", rel, n), T(n, vrel, v)], "r1_have"
    if k == 3:
        s = f"my {relw}'s name is {n} and {pro} {text} now".lower()
        return s, [T("my", rel, n.lower()), T(n.lower(), vrel, v.lower())], "r1_lower"
    if k == 4:
        o = nm.org()
        text, vrel, v = vp(r, nm, exclude=("employer", "occupation"))
        return (f"{n} joined {o} in {r.choice(MONTHS)}, and {pro} {text}.",
                [T(n, "employer", o), T(n, vrel, v)], "r1_joined")
    if k == 5:
        return (f"I bumped into {n} at the {r.choice(VENUES)}. {pro.capitalize()} {text}.",
                [T(n, vrel, v)], "r1_met")
    if k == 6:
        return f"Had a chat with {n} today, turns out {pro} {text}.", [T(n, vrel, v)], "r1_chat"
    owner = nm.first()
    return (f"{owner}'s {relw} is {n} and {pro} {text}.", [T(owner, rel, n), T(n, vrel, v)], "r1_poss")


AUX = {"city": "doesn't", "employer": "doesn't", "occupation": "doesn't", "language": "doesn't",
       "place_of_birth": "wasn't", "hometown": "doesn't"}


def r2_none(r, nm):
    k = r.randrange(9)
    n = nm.first() if r.random() < 0.6 else nm.person()
    pro = r.choice(["she", "he"])
    text, vrel, v = vp(r, nm)
    forms = {
        0: (f"{n} {text}, right?", "r2_right"),
        1: (f"{n} {text}, {AUX[vrel]} {pro}?", "r2_tag"),
        2: (f"{n} {text}, yeah?", "r2_yeah"),
        3: (f"so {n} {text}?".lower(), "r2_so"),
        4: (f"{n} {text}??", "r2_dbl"),
        5: (f"Wait, {n} {text}?", "r2_wait"),
        6: (f"so {n} {text} or what".lower(), "r2_noq_orwhat"),
        7: (f"hang on, {n} {text}, is that right".lower(), "r2_noq_isthat"),
        8: (f"{n} {text} or am i thinking of someone else".lower(), "r2_noq_someone"),
    }
    s, tid = forms[k]
    return s, ["NONE"], tid


def r2_stmt(r, nm):
    k = r.randrange(5)
    n = nm.first() if r.random() < 0.6 else nm.person()
    if k == 0:
        o = nm.org()
        return f"I know where {n} works: {o}.", [T(n, "employer", o)], "r2s_iknow"
    if k == 1:
        p = nm.place()
        return f"Guess where {n} lives? {p}!", [T(n, "city", p)], "r2s_guess"
    if k == 2:
        relw, rel, _ = pick_rel(r)
        m = nm.first()
        return f"You know who {n}'s {relw} is? It's {m}.", [T(n, rel, m)], "r2s_youknow"
    if k == 3:
        lang = r.choice(D.LANG)
        return f"Which language does {n} speak? {lang}, of course.", [T(n, "language", lang)], "r2s_which"
    p = nm.place()
    return f"Where was {n} born? In {p}.", [T(n, "place_of_birth", p)], "r2s_where"


def r3(r, nm):
    k = r.randrange(8)
    n = nm.first() if r.random() < 0.6 else nm.person()
    x = r.choice([nm.surname(), nm.place().split()[-1]])
    forms = [
        (f"{n} teaches at {x} School.", f"{x} School", "employer/work_location", "r3_teaches"),
        (f"{n} teaches history at {x} Academy.", f"{x} Academy", "employer/work_location", "r3_teaches_subj"),
        (f"{n} lectures at {x} University.", f"{x} University", "employer/work_location", "r3_lectures"),
        (f"{n} coaches at {x} Club.", f"{x} Club", "employer/work_location", "r3_coaches"),
        (f"{n} works at the {x} Library.", f"{x} Library", "employer/work_location", "r3_library"),
        (f"{n} studies at {x} College.", f"{x} College", "school/educated_at", "r3_studies"),
        (f"{n} is studying at {x} University.", f"{x} University", "school/educated_at", "r3_studying"),
        (f"{n} is enrolled at {x} Academy.", f"{x} Academy", "school/educated_at", "r3_enrolled"),
    ]
    s, v, rel, tid = forms[k]
    return s, [T(n, rel, v)], tid


def build(seed=2352, n_base=900, n_r1=90, n_r2=70, n_r2s=20, n_r3=60):
    r = random.Random(seed)
    nm = D.Names(r)
    base = [json.loads(x) for x in BASE_DEV.read_text().splitlines() if x.strip()]
    r.shuffle(base)
    rows = [dict(row, tag="base") for row in base[:n_base]]
    seen = {row["turn"] for row in rows}
    for fn, n, tag, fam in [(r1, n_r1, "R1", "risk_teach"), (r2_none, n_r2, "R2", "risk_none"),
                            (r2_stmt, n_r2s, "R2s", "risk_teach"), (r3, n_r3, "R3", "risk_teach")]:
        got = 0
        while got < n:
            s, frames, tid = fn(r, nm)
            if s in seen:
                continue
            seen.add(s)
            rows.append(dict(turn=s, frames=frames, family=fam, tid=tid, tag=tag))
            got += 1
    for i, row in enumerate(rows):
        row["id"] = f"d{i:04d}"
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = build()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(x) + "\n" for x in rows))
    (out.parent / "dev235b_turns.json").write_text(json.dumps([{"id": x["id"], "turn": x["turn"]} for x in rows]))
    from collections import Counter
    print(len(rows), Counter(x["tag"] for x in rows))


if __name__ == "__main__":
    main()
