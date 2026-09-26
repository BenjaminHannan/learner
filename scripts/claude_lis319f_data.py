#!/usr/bin/env python3
"""lis-319f training data = lis-319's data with a FORMER mode (the one change: "used to" is no longer saved as now).

Why (Ben's pasted report, 09-26 12:00 UTC, checked against the data): the reader's modes cannot say "used to", and its
training labels teach former jobs and homes as current ("he was a fisherman out of Peterhead his whole life" ->
occupation fisherman, ASSERT). On readpanel319c, 3 of the 7 whole-claim wrong saves were former jobs saved as current.

Steps (all code, no new model- or Claude-written text):
  1. Read lis-319's built data (claude_lis319_data.py output: train.jsonl, dev.jsonl), unchanged prompts.
  2. RELABEL: a fact whose rel is time-bound (CURRENT_RELS) gets mode FORMER when the clause holding its value has a
     past cue (PAST_ANY, or the rel group's own cues) and no present cue (still, now, currently, has/have worked...).
     A value that already carries the time ("retired judge", "ex-boss") is left alone. Everything else is unchanged.
  3. TEMPLATES: --n-train / --n-dev single-turn rows made by code from the data's own name and value pools: former
     sentences (FORMER), former + current pairs ("used to live in X, now lives in Y"), and look-alike current sentences
     ("has worked at X for 6 years", "moved to X last year", "still lives in X") that stay ASSERT.
FORMER is not in the compiler's WRITE_MODES, so FORMER facts are held, never saved (no compiler change).

python3 scripts/claude_lis319f_data.py --base WORK/data --out WORK/data319f [--n-train 1200 --n-dev 150]
        [--audit OUT.jsonl]   also writes relabel samples for the blind audit (train rows only)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from claude_lis300_common import frame_text  # noqa: E402
from claude_lis319_common import build_prompt_hist  # noqa: E402

WORK_RELS = {"occupation", "employer", "work_location", "title"}
HOME_RELS = {"city", "home"}
PERSON_RELS = {"boss", "teacher", "coach", "head_coach", "tutor", "landlord", "roommate", "neighbour", "partner",
               "fiance", "classmate", "teammate", "mentor", "babysitter", "therapist", "doctor", "dentist", "vet",
               "colleague", "school"}
THING_RELS = {"cat", "dog", "hamster", "horse", "parrot", "rabbit", "pet", "car", "hobby", "instrument", "sport"}
CURRENT_RELS = WORK_RELS | HOME_RELS | PERSON_RELS | THING_RELS

USED_TO = r"used to (?:be|work|live|have|go|drive|teach|play|run|own|coach|date|do|rent|study)"
PAST_ANY = re.compile(r"\b(" + USED_TO + r"|formerly|back then|back in the day|years ago|in the past|previously|"
                      r"before (?:this|that|my|his|her|their|the) (?:job|move)|till last year|until last year)\b", re.I)
# group cues must sit in the few words just before the value (PRE_WORDS), so a cue about something else in the same
# sentence ("had a dog that looked like my dog Gizmo", "since my coworker quit") does not count
PRE_WORDS = 7
PAST_PRE = {
    "work": re.compile(r"\b(retired|was an?|were an?|worked|quit|left|got laid off from|got fired from|was at)\b", re.I),
    "home": re.compile(r"\b(lived|moved (?:away )?from|left)\b", re.I),
    "person": None,   # built per relation: "old <rel word>", "was my <rel word>"
    "thing": re.compile(r"\b(had an?|sold (?:my|his|her|their|our)|lost (?:my|his|her|their|our))\b", re.I),
}
PAST_AFTER_THING = re.compile(r"^\W*(?:\w+\W+){0,4}?(died|passed away)\b", re.I)
PRESENT = re.compile(r"\b(still|now|currently|these days|has worked|have worked|'s worked|'ve worked|has lived|"
                     r"have lived|'s lived|'ve lived|has been|have been)\b", re.I)
CLAUSE_SPLIT = re.compile(r"[.!?;(]+|\)|\s[-–—]\s|,|\s(?:but|and now|now|though|although|while|whereas)\s", re.I)
VALUE_HAS_TIME = re.compile(r"\b(retired|former|ex|old)\b|^ex-", re.I)


def group_of(rel):
    return ("work" if rel in WORK_RELS else "home" if rel in HOME_RELS else
            "person" if rel in PERSON_RELS else "thing" if rel in THING_RELS else None)


def clause_parts(turn: str, value: str):
    """(clause text before the value, clause text after it) for the first whole-word occurrence of value, or None."""
    m = re.search(r"(?<![A-Za-z0-9])" + re.escape(value.strip()) + r"(?![A-Za-z0-9])", turn)
    if not m:
        return None
    cuts = [0] + [x.end() for x in CLAUSE_SPLIT.finditer(turn) if x.end() <= m.start()]
    lo = max(cuts)
    hi = min([x.start() for x in CLAUSE_SPLIT.finditer(turn) if x.start() >= m.end()] + [len(turn)])
    return turn[lo:m.start()], turn[m.end():hi]


def is_former(f: dict, turn: str) -> bool:
    rel, val = f.get("rel"), str(f.get("value", ""))
    if f.get("mode") not in ("ASSERT", "CORRECT") or rel not in CURRENT_RELS or not val.strip():
        return False
    if VALUE_HAS_TIME.search(val):
        return False
    parts = clause_parts(turn, val)
    if parts is None:
        return False
    before, after = parts
    if PRESENT.search(before + " " + after):
        return False
    if PAST_ANY.search(before + " " + after):
        return True
    pre = " ".join(before.split()[-PRE_WORDS:])
    g = group_of(rel)
    if g == "person":
        rw = r"(?:\w+\s+)?" + re.escape(rel.replace("_", " "))
        old_pre = re.compile(r"(?<!-)\bold\s+" + rw + r"\s*$", re.I)          # "my old roommate Asuka"
        was_after = re.compile(r"^\s*(?:was|used to be)\s+(?:my|his|her|their|our)\s+" + rw + r"\b", re.I)
        return bool(old_pre.search(pre) or was_after.match(after))
    if g == "thing" and PAST_AFTER_THING.search(after):
        return True
    return bool(PAST_PRE[g].search(pre))


def split_prompt(prompt):
    head, turn = prompt.rsplit("\nUser said: ", 1)
    return turn[: -len("\nFrame: ")] if turn.endswith("\nFrame: ") else turn


def parse_target(t):
    return json.loads(t.split("\n<END>")[0].split("<END>")[0])


def relabel(rows, audit=None):
    c = Counter()
    out = []
    for r in rows:
        fr = parse_target(r["target"])
        turn = split_prompt(r["prompt"])
        changed = False
        for f in fr.get("facts") or []:
            if is_former(f, turn):
                f["mode"] = "FORMER"
                f.pop("old", None)
                changed = True
                c[f"former:{f['rel']}"] += 1
        if changed:
            if fr.get("act") in ("STATE", "CORRECT") and not any(
                    f.get("mode") in ("ASSERT", "CORRECT") for f in fr.get("facts") or []):
                fr["act"] = "STATE"
            c["rows_relabelled"] += 1
            c[f"rows_relabelled:{r['src']}"] += 1
            r = dict(r, target=frame_text(fr), relabel="former")
            if audit is not None:
                audit.append(r)
        out.append(r)
    return out, c


# ---------------------------------------------------------------- templates
MONTHS = ["January", "March", "May", "June", "August", "October", "November"]


def pools(rows):
    """Value pools from the built data's own labels (all sources, unique prompts), kept only when a value was labelled
    at least twice, values from the non-o0b sources only (o0b values are random names and typos): occupations in lower case, names/cities/employers capitalised."""
    cnt, seen = Counter(), set()
    for r in rows:
        if r["prompt"] in seen:
            continue
        seen.add(r["prompt"])
        for f in parse_target(r["target"]).get("facts") or []:
            if f.get("mode") != "ASSERT":
                continue
            v, o = str(f.get("value", "")).strip(), str(f.get("owner", "")).strip()
            rel = f.get("rel")
            if r["src"] == "o0b":          # o0b values are random names and deliberate typos; its owners are fine
                rel = None
            if rel == "occupation" and re.fullmatch(r"[a-z]+(?: [a-z]+){0,2}", v) and "retired" not in v:
                cnt[("occupation", v)] += 1
            elif rel in ("city", "employer") and re.fullmatch(r"[A-Z][a-z]+(?: [A-Z][a-z]+){0,2}", v):
                cnt[(rel, v)] += 1
            elif rel in ("dog", "cat", "rabbit", "hamster", "parrot") and re.fullmatch(r"[A-Z][a-z]+", v):
                cnt[(rel, v)] += 1
            if o.lower() != "me" and re.fullmatch(r"[A-Z][a-z]{2,}", o):
                cnt[("_name", o)] += 1
    P = {}
    for (k, v), n in cnt.items():
        if n >= 2:
            P.setdefault(k, []).append(v)
    return {k: sorted(v) for k, v in P.items()}


def owner_forms(rng, P):
    if rng.random() < 0.4:
        return "me", "I", "I", "my", "have"
    nm = rng.choice(P["_name"])
    return nm, nm, rng.choice(["she", "he"]), None, "has"


def tpl_rows(n, rng, P, tag):
    out = []
    kinds = ["job", "employer", "city", "person", "pet", "pair", "c_employer", "c_city", "c_job"]
    wts = [16, 14, 14, 12, 8, 12, 9, 8, 7]
    for i in range(n):
        k = rng.choices(kinds, wts)[0]
        o, O, pron, poss, have = owner_forms(rng, P)
        yrs = rng.choice([2, 3, 5, 6, 8, 12, 20, 40])
        facts = []
        if k == "job":
            v = rng.choice(P["occupation"])
            art = "an" if v[:1].lower() in "aeiou" else "a"
            t = rng.choice([f"{O} used to be {art} {v}", f"{O} was {art} {v} for {yrs} years",
                            f"before this job {O} was {art} {v}", f"{O} worked as {art} {v} back in the day"])
            facts = [(o, "occupation", v, "FORMER")]
        elif k == "employer":
            v = rng.choice(P["employer"])
            t = rng.choice([f"{O} used to work at {v}", f"{O} left {v} in {rng.choice(MONTHS)}",
                            f"{O} worked for {v} until last year", f"{O} was at {v} for {yrs} years before switching"])
            facts = [(o, "employer", v, "FORMER")]
        elif k == "city":
            v = rng.choice(P["city"])
            t = rng.choice([f"{O} used to live in {v}", f"{O} lived in {v} till last year",
                            f"{O} moved away from {v} in {rng.choice(MONTHS)}"])
            facts = [(o, "city", v, "FORMER")]
        elif k == "person":
            rel = rng.choice(["boss", "teacher", "coach", "landlord", "roommate", "neighbour", "tutor", "mentor"])
            v = rng.choice(P["_name"])
            if O != "I":
                t = rng.choice([f"{v} was {O}'s {rel} back then", f"{v} used to be {O}'s {rel}"])
            else:
                t = rng.choice([f"{v} was my {rel} back then", f"{v} used to be my {rel}", f"my old {rel} was {v}"])
            facts = [(o, rel, v, "FORMER")]
        elif k == "pet":
            rel = rng.choice(["dog", "cat"])
            v = rng.choice(P[rel])
            t = rng.choice([f"{O} had a {rel} called {v} but it died last spring",
                            f"{O} used to have a {rel} named {v}"])
            facts = [(o, rel, v, "FORMER")]
        elif k == "pair":
            a, b = rng.sample(P["city"], 2)
            if O == "I":
                t = f"I used to live in {a}, now I live in {b}"
            else:
                t = f"{O} used to live in {a}, now {pron} lives in {b}"
            facts = [(o, "city", a, "FORMER"), (o, "city", b, "ASSERT")]
        elif k == "c_employer":
            v = rng.choice(P["employer"])
            t = rng.choice([f"{O} {have} worked at {v} for {yrs} years", f"{O} still {'work' if O == 'I' else 'works'} at {v}",
                            f"{O} {'started' if rng.random() < .5 else 'just started'} at {v} last month"])
            facts = [(o, "employer", v, "ASSERT")]
        elif k == "c_city":
            v = rng.choice(P["city"])
            t = rng.choice([f"{O} moved to {v} last year", f"{O} still {'live' if O == 'I' else 'lives'} in {v}",
                            f"{O} {have} lived in {v} for {yrs} years"])
            facts = [(o, "city", v, "ASSERT")]
        else:
            v = rng.choice(P["occupation"])
            art = "an" if v[:1].lower() in "aeiou" else "a"
            t = rng.choice([f"{O} {have} been {art} {v} for {yrs} years", f"{O} {'am' if O == 'I' else 'is'} {art} {v} now",
                            f"{O} became {art} {v} last year"])
            facts = [(o, "occupation", v, "ASSERT")]
        t = t[0].upper() + t[1:] if rng.random() < 0.5 else t
        fr = {"act": "STATE", "facts": [{"owner": a, "rel": b, "value": c, "mode": d} for a, b, c, d in facts],
              "ask": None}
        out.append({"id": f"f319-{tag}-{i:05d}", "prompt": build_prompt_hist(t, "", None), "target": frame_text(fr),
                    "src": f"former319{'' if tag == 'train' else '_dev'}", "family": f"former_{k}", "turn": t,
                    "prev_reply": "", "frame": fr, "history": []})
    return out


def read_jsonl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-train", type=int, default=1200)
    ap.add_argument("--n-dev", type=int, default=150)
    ap.add_argument("--seed", type=int, default=319)
    ap.add_argument("--audit")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    train, dev = read_jsonl(Path(a.base) / "train.jsonl"), read_jsonl(Path(a.base) / "dev.jsonl")
    aud = []
    train2, ct = relabel(train, aud)
    dev2, cd = relabel(dev)
    P = pools(train)
    t_tr, t_dev = tpl_rows(a.n_train, rng, P, "train"), tpl_rows(a.n_dev, rng, P, "dev")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    train3 = train2 + t_tr
    rng.shuffle(train3)
    (out / "train.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in train3), encoding="utf-8")
    (out / "dev.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in dev2 + t_dev),
                                   encoding="utf-8")
    if a.audit:
        seen, uniq = set(), []
        for r in aud:
            if r["prompt"] not in seen:
                seen.add(r["prompt"])
                uniq.append(r)
        Path(a.audit).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in uniq), encoding="utf-8")
    fam = Counter(r["family"] for r in t_tr)
    print(json.dumps({"train": len(train3), "dev": len(dev2) + len(t_dev), "train_relabel": dict(sorted(ct.items())),
                      "dev_relabel": dict(sorted(cd.items())), "templates_train": dict(sorted(fam.items()))}, indent=1))


if __name__ == "__main__":
    main()
