#!/usr/bin/env python3
"""Five checks of spec 331 for gram360 bank G (letters E to J). Run from anywhere: python3 check_bank.py"""
import json, math, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
LO, HI = "E", "J"
N_LIVES = 10
TURN_KEYS = {"life_id", "day", "turn_index", "user_text", "kind", "ask_type", "facts", "gold", "creative_seed_facts"}
TRUTH_KEYS = {"fact_id", "life_id", "owner", "relation", "value", "taught_turn", "valid_until_turn"}
FACT_KEYS = {"owner", "relation", "value"}
GOLD_KEYS = {"values", "type", "uses_facts"}
KINDS = {"teach", "correct", "nosave", "ask", "smalltalk", "creative", "other"}
ASK_TYPES = {"one_hop", "two_hop", "reversal", "edit", "yesno", "never_told", "partial"}
GOLD_TYPE = {"one_hop": {"value"}, "two_hop": {"value"}, "reversal": {"value"}, "edit": {"value"},
             "yesno": {"yes", "no"}, "never_told": {"idk"}, "partial": {"partial"}}
# spec 331 bank-of-40 minimums; this bank is a quarter of that, so each is divided by 4 and rounded up
SPEC_MIN = {"teach": 140, "correct": 25, "nosave": 25, "smalltalk": 50, "creative": 30,
            "one_hop": 60, "two_hop": 35, "reversal": 25, "edit": 25, "yesno": 15, "never_told": 30, "partial": 10,
            "edit_two_hop": 10, "teach_single": 70, "teach_multi": 40, "day3_on_day1": 60}
MIN = {k: math.ceil(v / 4) for k, v in SPEC_MIN.items()}
MIN["ask"] = sum(MIN[a] for a in ASK_TYPES)
# capitalised words allowed anywhere in user text without being a name
STOP = {"I", "I'm", "I'd", "I've", "I'll", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
        "Sunday", "January", "February", "March", "April", "May", "June", "July", "August", "September",
        "October", "November", "December", "Christmas"}


def load(name):
    rows, errs = [], []
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            try:
                rows.append(json.loads(line))
            except Exception as e:  # noqa
                errs.append(f"{name}:{i} does not parse ({e})")
    return rows, errs


def check1(turns, truth, errs):
    for t in turns:
        where = f"{t.get('life_id')} t{t.get('turn_index')}"
        if set(t) != TURN_KEYS:
            errs.append(f"{where}: keys {sorted(set(t) ^ TURN_KEYS)}")
            continue
        if t["kind"] not in KINDS: errs.append(f"{where}: bad kind")
        if t["day"] not in (1, 2, 3): errs.append(f"{where}: bad day")
        if not isinstance(t["user_text"], str) or not t["user_text"].strip(): errs.append(f"{where}: empty text")
        if t["kind"] == "ask":
            if t["ask_type"] not in ASK_TYPES: errs.append(f"{where}: bad ask_type")
            g = t["gold"]
            if not isinstance(g, dict) or set(g) != GOLD_KEYS: errs.append(f"{where}: gold keys"); continue
            if g["type"] not in GOLD_TYPE.get(t["ask_type"], set()): errs.append(f"{where}: gold type {g['type']}")
            if t["ask_type"] in ("yesno", "never_told") and g["values"]: errs.append(f"{where}: values should be empty")
            if t["ask_type"] not in ("yesno", "never_told") and not g["values"]: errs.append(f"{where}: no values")
            if t["ask_type"] == "never_told" and g["uses_facts"]: errs.append(f"{where}: never_told cites facts")
            if t["ask_type"] != "never_told" and not g["uses_facts"]: errs.append(f"{where}: no uses_facts")
        else:
            if t["ask_type"] is not None or t["gold"] is not None: errs.append(f"{where}: ask fields on non-ask")
        if t["kind"] in ("teach", "correct"):
            if not t["facts"]: errs.append(f"{where}: no facts")
            for f in t["facts"]:
                if set(f) != FACT_KEYS or not all(isinstance(f[k], str) and f[k] for k in FACT_KEYS):
                    errs.append(f"{where}: fact keys")
        elif t["facts"]:
            errs.append(f"{where}: facts on non-teach")
        if t["kind"] != "creative" and t["creative_seed_facts"]: errs.append(f"{where}: seeds on non-creative")
        if t["kind"] == "creative" and not t["creative_seed_facts"]: errs.append(f"{where}: creative without seeds")
    for r in truth:
        if set(r) != TRUTH_KEYS: errs.append(f"truth {r.get('fact_id')}: keys")
    # turn order, days and per-life shape
    by_life = defaultdict(list)
    for t in turns: by_life[t["life_id"]].append(t)
    want = [f"e2e-g360-{i:02d}" for i in range(1, N_LIVES + 1)]
    if sorted(by_life) != want: errs.append(f"life ids {sorted(by_life)}")
    for lid, ts in by_life.items():
        if [t["turn_index"] for t in ts] != list(range(len(ts))): errs.append(f"{lid}: turn_index not 0..n-1")
        if [t["day"] for t in ts] != sorted(t["day"] for t in ts): errs.append(f"{lid}: days out of order")
        per_day = Counter(t["day"] for t in ts)
        if not all(4 <= per_day[d] <= 7 for d in (1, 2, 3)): errs.append(f"{lid}: turns per day {dict(per_day)}")
    # every taught fact appears exactly once in truth, and vice versa; corrections close an old fact at that turn
    ids = Counter(r["fact_id"] for r in truth)
    for k, n in ids.items():
        if n > 1: errs.append(f"truth: {k} repeated")
        if not re.fullmatch(r"g360\d\d-f\d\d", k): errs.append(f"truth: bad id {k}")
    key = lambda lid, ti, o, r, v: (lid, ti, o, r, v)
    truth_keys = Counter(key(r["life_id"], r["taught_turn"], r["owner"], r["relation"], r["value"]) for r in truth)
    turn_keys = Counter(key(t["life_id"], t["turn_index"], f["owner"], f["relation"], f["value"])
                        for t in turns for f in t["facts"])
    if truth_keys != turn_keys: errs.append(f"truth vs turns facts differ: {list(((truth_keys - turn_keys) + (turn_keys - truth_keys)).elements())[:5]}")
    kind_at = {(t["life_id"], t["turn_index"]): t["kind"] for t in turns}
    closed_at = Counter()
    for r in truth:
        v = r["valid_until_turn"]
        if v is not None:
            if kind_at.get((r["life_id"], v)) != "correct" or v <= r["taught_turn"]:
                errs.append(f"{r['fact_id']}: closed at a turn that is not a later correction")
            closed_at[(r["life_id"], v)] += 1
    for (lid, ti), k in kind_at.items():
        if k == "correct" and closed_at[(lid, ti)] == 0: errs.append(f"{lid} t{ti}: correction closes nothing")


def facts_index(truth):
    return {r["fact_id"]: r for r in truth}


def check2(turns, truth, errs):
    F = facts_index(truth)
    for t in turns:
        cited = (t["gold"] or {}).get("uses_facts", []) + t["creative_seed_facts"]
        for fid in cited:
            r = F.get(fid)
            where = f"{t['life_id']} t{t['turn_index']} {fid}"
            if r is None: errs.append(f"{where}: missing"); continue
            if r["life_id"] != t["life_id"]: errs.append(f"{where}: other life")
            if r["taught_turn"] >= t["turn_index"]: errs.append(f"{where}: not taught before")
            if r["valid_until_turn"] is not None and r["valid_until_turn"] <= t["turn_index"]:
                errs.append(f"{where}: closed before the ask")


def check3(turns, truth, errs):
    F = facts_index(truth)
    for t in turns:
        if t["kind"] != "ask": continue
        g = t["gold"]
        cited = [F[f] for f in g["uses_facts"] if f in F]
        for v in g["values"]:
            if t["ask_type"] == "reversal":
                ok = any(r["owner"] == v for r in cited)
            else:
                ok = any(r["value"] == v for r in cited)
            if not ok: errs.append(f"{t['life_id']} t{t['turn_index']}: value {v!r} not in cited facts")
        if t["ask_type"] in ("two_hop",) or (t["ask_type"] == "edit" and len(cited) > 1):
            # the hops must chain (a cited fact's value is another cited fact's owner) and the answer is the last hop
            vals = {r["value"] for r in cited}
            owners = {r["owner"] for r in cited}
            if not any(r["owner"] in vals for r in cited): errs.append(f"{t['life_id']} t{t['turn_index']}: hops do not chain")
            last = {r["value"] for r in cited if r["value"] not in owners}
            if not all(v in last for v in g["values"]): errs.append(f"{t['life_id']} t{t['turn_index']}: answer is not the last hop")
        if t["ask_type"] == "edit":
            corrected = [r for r in cited if (t["life_id"], r["taught_turn"]) in
                         {(x["life_id"], x["turn_index"]) for x in turns if x["kind"] == "correct"}]
            if not corrected: errs.append(f"{t['life_id']} t{t['turn_index']}: edit does not cite a corrected fact")
            elif not any(v == r["value"] for v in g["values"] for r in corrected):
                errs.append(f"{t['life_id']} t{t['turn_index']}: edit answer is not the corrected value")


def in_range(s):
    return LO <= s[0] <= HI


def check4(turns, truth, errs):
    names_by_life = defaultdict(set)   # first word of every name (owner or capitalised value)
    words_by_life = defaultdict(set)   # every word of every name
    for r in truth:
        items = [r["value"]] + ([] if r["owner"] == "USER" else [r["owner"]])
        for s in items:
            if not s[0].isupper():
                continue
            if not in_range(s): errs.append(f"{r['fact_id']}: name {s!r} outside {LO}-{HI}")
            names_by_life[r["life_id"]].add(s.split()[0])
            words_by_life[r["life_id"]].update(re.findall(r"[A-Za-z]+", s))
        if r["owner"] != "USER" and not r["owner"][0].isupper():
            errs.append(f"{r['fact_id']}: owner {r['owner']!r} not a capitalised name")
    seen = defaultdict(set)
    for lid, ns in names_by_life.items():
        for n in ns: seen[n].add(lid)
    for n, lids in seen.items():
        if len(lids) > 1: errs.append(f"name {n!r} repeats across lives {sorted(lids)}")
    # capitalised words in the user's text: mid-sentence ones must be names in range, and no other life's name may appear
    for t in turns:
        text = t["user_text"]
        for m in re.finditer(r"[A-Za-z][A-Za-z']*", text):
            w = m.group(0)
            before = text[:m.start()].rstrip(" (\"'")
            initial = before == "" or before[-1] in ".!?:"
            base = w.split("'")[0]
            for other, ns in names_by_life.items():
                if other != t["life_id"] and base in ns:
                    errs.append(f"{t['life_id']} t{t['turn_index']}: uses {base!r}, a name from {other}")
            if not w[0].isupper() or initial or w in STOP or base in STOP:
                continue
            if base in words_by_life[t["life_id"]]:
                continue
            if not in_range(w): errs.append(f"{t['life_id']} t{t['turn_index']}: capitalised {w!r} outside {LO}-{HI}")


def counts(turns, truth):
    F = facts_index(truth)
    c = Counter(t["kind"] for t in turns)
    c.update(t["ask_type"] for t in turns if t["kind"] == "ask")
    corrected_ids = set()
    corr_turns = {(t["life_id"], t["turn_index"]) for t in turns if t["kind"] == "correct"}
    for r in truth:
        if (r["life_id"], r["taught_turn"]) in corr_turns: corrected_ids.add(r["fact_id"])
    c["edit_two_hop"] = sum(1 for t in turns if t["ask_type"] == "edit" and len(t["gold"]["uses_facts"]) >= 2
                            and corrected_ids & set(t["gold"]["uses_facts"]))
    c["teach_single"] = sum(1 for t in turns if t["kind"] == "teach" and len(t["facts"]) == 1)
    c["teach_multi"] = sum(1 for t in turns if t["kind"] == "teach" and len(t["facts"]) >= 2)
    day1 = {(t["life_id"], t["turn_index"]) for t in turns if t["day"] == 1}
    c["day3_on_day1"] = sum(1 for t in turns if t["kind"] == "ask" and t["day"] == 3 and t["gold"]["uses_facts"]
                            and all((F[f]["life_id"], F[f]["taught_turn"]) in day1 for f in t["gold"]["uses_facts"]))
    return c


def check5(turns, truth, errs):
    c = counts(turns, truth)
    for k, m in MIN.items():
        if c[k] < m: errs.append(f"{k}: {c[k]} < minimum {m}")
    return c


def main():
    turns, e1 = load("turns.jsonl")
    truth, e1b = load("truth.jsonl")
    results = []
    errs = e1 + e1b
    if not errs: check1(turns, truth, errs)
    results.append(("1. Every line parses and has exactly the spec keys", errs))
    ok_struct = not errs
    for name, fn in [("2. Every uses_facts id exists, was taught before the ask and was not closed before it", check2),
                     ("3. Every gold value equals the value (or, for reversal, the owner) of a fact it cites, after corrections", check3),
                     ("4. Every name obeys E to J and no name repeats across lives", check4)]:
        e = []
        if ok_struct: fn(turns, truth, e)
        else: e.append("skipped: check 1 failed")
        results.append((name, e))
    e5 = []
    c = check5(turns, truth, e5) if ok_struct else Counter()
    results.append(("5. Kind and ask_type minimums (spec / 4, rounded up) are met", e5))
    print(f"turns {len(turns)}, facts {len(truth)}, closed {sum(1 for r in truth if r['valid_until_turn'] is not None)}")
    for k in ["teach", "correct", "nosave", "ask", "smalltalk", "creative", "other"]:
        print(f"  kind {k}: {c[k]} (min {MIN.get(k, '-')})")
    for k in ["one_hop", "two_hop", "reversal", "edit", "yesno", "never_told", "partial"]:
        print(f"  ask_type {k}: {c[k]} (min {MIN[k]})")
    for k in ["edit_two_hop", "teach_single", "teach_multi", "day3_on_day1"]:
        print(f"  {k}: {c[k]} (min {MIN[k]})")
    all_ok = True
    for name, e in results:
        print(f"{name}: {'pass' if not e else 'FAIL'}")
        for x in e[:30]: print("    " + x)
        all_ok &= not e
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
