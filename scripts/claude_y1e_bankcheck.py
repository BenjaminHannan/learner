#!/usr/bin/env python3
"""Bank checker for 331-format conversation banks (Answering-from-memory thread, 2026-09-26). New file.

Runs the spec's five writer checks (design/v3/30-modes/331-e2e-bank-spec.md) plus structure checks on one or more
folders holding turns.jsonl + truth.jsonl (or turns_v2.jsonl + truth_v2.jsonl with --v2). Prints COUNTS AND IDS ONLY
(life_id, turn_index, fact_id, check name): never user text, names or values, so a builder may run it on a
TEST-ONLY bank without reading it.

  python -B scripts/claude_y1e_bankcheck.py FOLDER [FOLDER ...] [--lives N] [--prefix e2e-e-] [--v2]
Minimums scale with the number of lives: bank minimum x N / 40, rounded up (a 10-life part needs a quarter).
Last line: "CHECK OK <n> checks" or "CHECK FAIL <k> of <n> checks".
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

TURN_KEYS = {"life_id", "day", "turn_index", "user_text", "kind", "ask_type", "facts", "gold", "creative_seed_facts"}
TRUTH_KEYS = {"fact_id", "life_id", "owner", "relation", "value", "taught_turn", "valid_until_turn"}
KINDS = {"teach", "correct", "nosave", "ask", "smalltalk", "creative", "other"}
ASK_TYPES = {"one_hop", "two_hop", "reversal", "edit", "yesno", "never_told", "partial"}
BANK_MIN = {"teach": 140, "correct": 25, "nosave": 25, "smalltalk": 50, "creative": 30,
            "one_hop": 60, "two_hop": 35, "reversal": 25, "edit": 25, "yesno": 15, "never_told": 30, "partial": 10,
            "day3_on_day1": 60, "edit_two_hop": 10}
GOLD_TYPE = {"one_hop": {"value"}, "two_hop": {"value"}, "reversal": {"value"}, "edit": {"value"},
             "yesno": {"yes", "no"}, "never_told": {"idk"}, "partial": {"partial"}}


def load(p: Path) -> tuple[list, int]:
    rows, bad = [], 0
    for x in p.read_text(encoding="utf-8").splitlines():
        if not x.strip():
            continue
        try:
            rows.append(json.loads(x))
        except ValueError:
            bad += 1
    return rows, bad


def low(s) -> str:
    return str(s).strip().lower()


def check(folders: list[str], n_lives: int | None, prefix: str | None, v2: bool) -> bool:
    turns, truth, parse_bad = [], [], 0
    for f in folders:
        t, b1 = load(Path(f) / ("turns_v2.jsonl" if v2 else "turns.jsonl"))
        r, b2 = load(Path(f) / ("truth_v2.jsonl" if v2 else "truth.jsonl"))
        turns += t
        truth += r
        parse_bad += b1 + b2
    res = []

    def rec(name, bad_ids):
        res.append((name, len(bad_ids)))
        print(f"{'ok  ' if not bad_ids else 'FAIL'} {name}: {len(bad_ids)} bad" +
              (f" {sorted(map(str, bad_ids))[:25]}" if bad_ids else ""))

    lives = defaultdict(list)
    for t in turns:
        lives[t.get("life_id")].append(t)
    for v in lives.values():
        v.sort(key=lambda t: t.get("turn_index", -1))
    n = n_lives or len(lives)
    print(f"lives {len(lives)}, turns {len(turns)}, facts {len(truth)}, closed {sum(1 for f in truth if f.get('valid_until_turn') is not None)}")
    tid = lambda t: f"{t.get('life_id')}/t{t.get('turn_index')}"  # noqa: E731

    # 1 parse + exact keys + types
    bad = [tid(t) for t in turns if set(t) != TURN_KEYS or t.get("kind") not in KINDS
           or not isinstance(t.get("user_text"), str) or not t["user_text"].strip()]
    bad += [f.get("fact_id") for f in truth if set(f) != TRUTH_KEYS]
    bad += ["parse"] * parse_bad
    rec("1 parse and exact keys", bad)
    # life ids
    bad = [l for l in lives if prefix and not re.fullmatch(re.escape(prefix) + r"\d\d", str(l))]
    if n_lives and len(lives) != n_lives:
        bad.append(f"lives={len(lives)}")
    rec("life ids", bad)
    # structure: contiguous turn_index, days 1-3 in order, 4-7 turns a day
    bad = []
    for l, ts in lives.items():
        if [t["turn_index"] for t in ts] != list(range(len(ts))):
            bad.append(f"{l}:index")
        days = [t["day"] for t in ts]
        c = Counter(days)
        if days != sorted(days) or sorted(c) != [1, 2, 3] or any(not 4 <= v <= 7 for v in c.values()):
            bad.append(f"{l}:days")
    rec("structure (3 days, 4-7 turns a day, contiguous turn_index)", bad)
    # field shapes per kind
    bad = []
    for t in turns:
        k, a = t.get("kind"), t.get("ask_type")
        if k == "ask":
            g = t.get("gold")
            if a not in ASK_TYPES or not isinstance(g, dict) or set(g) != {"values", "type", "uses_facts"} \
                    or g.get("type") not in GOLD_TYPE[a] or t.get("facts") != []:
                bad.append(tid(t))
            elif a in ("yesno", "never_told") and g["values"] != []:
                bad.append(tid(t))
            elif a == "never_told" and g["uses_facts"] != []:
                bad.append(tid(t))
            elif a not in ("yesno", "never_told") and (not g["values"] or not g["uses_facts"]):
                bad.append(tid(t))
        else:
            if a is not None or t.get("gold") is not None:
                bad.append(tid(t))
            if k in ("teach", "correct"):
                fs = t.get("facts")
                if not fs or any(set(x) != {"owner", "relation", "value"} for x in fs):
                    bad.append(tid(t))
            elif t.get("facts") != []:
                bad.append(tid(t))
            if k != "creative" and t.get("creative_seed_facts") != []:
                bad.append(tid(t))
    rec("field shapes per kind", bad)
    # truth <-> facts lists
    fid = {}
    dup = [f["fact_id"] for f in truth if f["fact_id"] in fid or fid.setdefault(f["fact_id"], f) is None]
    tk = {(t["life_id"], t["turn_index"]): t for t in turns}
    bad = list(dup)
    listed = Counter()
    for t in turns:
        for x in t.get("facts") or []:
            m = [f for f in truth if f["life_id"] == t["life_id"] and f["taught_turn"] == t["turn_index"]
                 and low(f["owner"]) == low(x["owner"]) and low(f["relation"]) == low(x["relation"])
                 and low(f["value"]) == low(x["value"])]
            if len(m) != 1:
                bad.append(tid(t))
            else:
                listed[m[0]["fact_id"]] += 1
    bad += [f["fact_id"] for f in truth if listed[f["fact_id"]] != 1]
    bad += [f["fact_id"] for f in truth if (f["life_id"], f["taught_turn"]) not in tk
            or tk[(f["life_id"], f["taught_turn"])]["kind"] not in ("teach", "correct")]
    for f in truth:
        v = f.get("valid_until_turn")
        if v is not None and ((f["life_id"], v) not in tk or tk[(f["life_id"], v)]["kind"] != "correct"
                              or v <= f["taught_turn"]):
            bad.append(f["fact_id"])
    rec("truth sheet matches the facts lists; corrections close at a correct turn", bad)
    # 2 uses_facts exist, taught before the ask, open at it
    bad = []
    for t in turns:
        if t.get("kind") != "ask" or not isinstance(t.get("gold"), dict):
            continue
        for u in t["gold"].get("uses_facts") or []:
            f = fid.get(u)
            if f is None or f["life_id"] != t["life_id"] or f["taught_turn"] >= t["turn_index"] \
                    or (f["valid_until_turn"] is not None and f["valid_until_turn"] <= t["turn_index"]):
                bad.append(f"{tid(t)}:{u}")
    rec("2 uses_facts exist, taught before, not closed", bad)
    # 3 gold values come from a cited fact (value, or owner for reversal)
    bad = []
    for t in turns:
        if t.get("kind") != "ask" or not isinstance(t.get("gold"), dict):
            continue
        cited = [fid[u] for u in t["gold"].get("uses_facts") or [] if u in fid]
        pool = {low(f["value"]) for f in cited} | {low(f["owner"]) for f in cited}
        if any(low(v) not in pool for v in t["gold"].get("values") or []):
            bad.append(tid(t))
    rec("3 gold values equal a cited fact's value (or owner)", bad)
    # 4 no person owner repeats across lives (names are not printed)
    owners = defaultdict(set)
    for f in truth:
        if f["owner"] != "USER":
            owners[low(f["owner"]).split()[0]].add(f["life_id"])
    bad = [f"name#{i}" for i, (k, v) in enumerate(sorted(owners.items())) if len(v) > 1]
    rec("4 no owner first name shared between lives", bad)
    # 5 minimums (scaled)
    scale = n / 40.0
    kc = Counter(t["kind"] for t in turns)
    ac = Counter(t["ask_type"] for t in turns if t["kind"] == "ask")
    d31 = sum(1 for t in turns if t["kind"] == "ask" and t["day"] == 3 and isinstance(t.get("gold"), dict)
              and t["gold"].get("uses_facts")
              and all(fid.get(u) and tk.get((t["life_id"], fid[u]["taught_turn"]), {}).get("day") == 1
                      for u in t["gold"]["uses_facts"]))
    e2 = sum(1 for t in turns if t.get("ask_type") == "edit" and len(t["gold"].get("uses_facts") or []) >= 2)
    have = dict(kc)
    have.update(ac)
    have["day3_on_day1"] = d31
    have["edit_two_hop"] = e2
    bad = [f"{k}:{have.get(k, 0)}<{math.ceil(m * scale)}" for k, m in BANK_MIN.items()
           if have.get(k, 0) < math.ceil(m * scale)]
    rec("5 kind and ask_type minimums (scaled)", bad)
    print("counts:", json.dumps({"kinds": dict(kc), "ask_types": dict(ac), "day3_on_day1": d31,
                                 "edit_two_hop": e2}, sort_keys=True))
    fails = sum(1 for _, b in res if b)
    print(f"CHECK OK {len(res)} checks" if not fails else f"CHECK FAIL {fails} of {len(res)} checks")
    return not fails


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--lives", type=int)
    ap.add_argument("--prefix")
    ap.add_argument("--v2", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if check(a.folders, a.lives, a.prefix, a.v2) else 1)


if __name__ == "__main__":
    main()
