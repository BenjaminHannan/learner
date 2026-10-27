#!/usr/bin/env python3
"""rsn-356: one-fact twins. make_twin(ep, rng, mode) returns a copy of a practice episode with ONE
support row edited so the right answer changes, re-solved by 296's independent solver (None if no
clean twin exists for this episode).

  mode "delete" (practice): delete one needed row.
      value1/value2 -> "I don't know"; count -> one fewer; correction (delete the newest) -> the older value.
  mode "change" (held out, evaluation only; never used in practice):
      value1/value2 -> the answer row's value changes; yesno -> the asked value flips yes/no;
      compare -> one number changes so the answer flips; count -> one member added;
      correction -> the two stamps swap so the other value is newest.
Other kinds get no twin (None).
"""
import copy
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn294_core as C  # noqa: E402
import claude_rsn296_gen as G  # noqa: E402

_K = C._key


def _sup_rows(ep):
    s = set(ep["gold"]["support"])
    return [r for r in ep["notebook"] if r["fid"] in s]


def _next_fid(ep):
    return "f%d" % (1 + max(int(r["fid"][1:]) for r in ep["notebook"]))


def _fresh_value(rng, rel, avoid):
    for _ in range(50):
        v = str(C.num_value(rng, rel) if rel in C.NUM_RELS else C.thing_value(rng, rel))
        if _K(v) not in avoid:
            return v
    return None


def make_twin(ep: dict, rng: random.Random, mode: str):
    cat, fr = ep["category"], ep["frame"]
    t = copy.deepcopy(ep)
    rows, sup = t["notebook"], _sup_rows(t)
    if not sup:
        return None
    if mode == "delete":
        if cat in ("value1", "value2"):
            gone = rng.choice(sup)
            t["notebook"] = [r for r in rows if r is not gone]
            t["gold"] = {"answer": "UNKNOWN", "support": []}
        elif cat == "count":
            if len(sup) < 2:
                return None
            gone = rng.choice(sup)
            t["notebook"] = [r for r in rows if r is not gone]
            t["gold"] = {"answer": str(len(sup) - 1), "support": [r["fid"] for r in sup if r is not gone]}
        elif cat == "correction":
            who, rel = fr["who"][0], fr["relations"][0]
            pair = [r for r in rows if _K(r["subject"]) == _K(who) and _K(r["relation"]) == _K(rel)]
            if len(pair) != 2:
                return None
            newest = max(pair, key=lambda r: int(r["when"]))
            older = [r for r in pair if r is not newest][0]
            t["notebook"] = [r for r in rows if r is not newest]
            t["gold"] = {"answer": older["value"], "support": [older["fid"]]}
        else:
            return None
    elif mode == "change":
        avoid = {_K(r["value"]) for r in rows} | {_K(r["subject"]) for r in rows}
        if cat in ("value1", "value2"):
            last = [r for r in sup if _K(r["relation"]) == _K(fr["relations"][-1])]
            if len(last) != 1:
                return None
            v = _fresh_value(rng, last[0]["relation"], avoid)
            if v is None:
                return None
            last[0]["value"] = v
            t["gold"] = {"answer": v, "support": list(ep["gold"]["support"])}
        elif cat == "yesno":
            row = sup[0]
            if _K(ep["gold"]["answer"]) == "yes":
                v = _fresh_value(rng, row["relation"], avoid) if row["relation"] not in C.PERSON_RELS else None
                if v is None:
                    v = "Zed Quorra"
                    if _K(v) in avoid:
                        return None
                row["value"] = v
                t["gold"] = {"answer": "no", "support": list(ep["gold"]["support"])}
            else:
                row["value"] = fr["value"]
                t["gold"] = {"answer": "yes", "support": list(ep["gold"]["support"])}
        elif cat == "compare":
            a, b = sup
            va, vb = float(a["value"]), float(b["value"])
            lo, hi = min(va, vb), max(va, vb)
            low_row = a if va == lo else b
            low_row["value"] = str(int(hi) + rng.randint(1, 5))      # the smaller one becomes the larger
            w = {_K(x): x for x in fr["who"]}
            va, vb = float(a["value"]), float(b["value"])
            win = a if (va > vb) == (fr["direction"] == "more") else b
            t["gold"] = {"answer": w.get(_K(win["subject"]), win["subject"]), "support": list(ep["gold"]["support"])}
        elif cat == "count":
            n = len(sup)
            if n + 1 > C.MAX_COUNT or len(rows) >= C.MAX_ROWS:
                return None
            fid = _next_fid(t)
            new = {"fid": fid, "subject": fr["who"][0], "relation": fr["relations"][0],
                   "value": "Zed Quorra", "when": 1 + max(int(r["when"]) for r in rows)}
            if _K(new["value"]) in avoid:
                return None
            rows.append(new)
            t["gold"] = {"answer": str(n + 1), "support": list(ep["gold"]["support"]) + [fid]}
        elif cat == "correction":
            who, rel = fr["who"][0], fr["relations"][0]
            pair = [r for r in rows if _K(r["subject"]) == _K(who) and _K(r["relation"]) == _K(rel)]
            if len(pair) != 2:
                return None
            pair[0]["when"], pair[1]["when"] = pair[1]["when"], pair[0]["when"]
            newest = max(pair, key=lambda r: int(r["when"]))
            t["gold"] = {"answer": newest["value"], "support": [newest["fid"]]}
        else:
            return None
    else:
        raise ValueError(mode)
    s = G.solve(t)
    if s is None or _K(s) != _K(t["gold"]["answer"]) or _K(s) == _K(ep["gold"]["answer"]):
        return None
    enc, infos = C.encode([t], random.Random(0))
    ga = C.gold_action(t, infos[0])
    if ga is None or _K(C.decode(ga, infos[0])) != _K(t["gold"]["answer"]):
        return None
    t["twin_of"] = mode
    return t


if __name__ == "__main__":
    import collections
    rng = random.Random(5)
    got = collections.Counter()
    for mode in ("delete", "change"):
        for k in ["value1", "value2", "yesno", "compare", "count", "correction", "who", "before"]:
            for _ in range(500):
                ep = C.gen_episode(rng, k)
                got[(mode, k)] += make_twin(ep, rng, mode) is not None
    for key, v in sorted(got.items()):
        print(key, v, "/ 500")
    print("selftest ok")
