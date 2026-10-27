#!/usr/bin/env python3
"""sf-401 panel checker (artifacts/claude-sf401-20260926/PANEL-SPEC.md). New file only. Prints COUNTS and ids only,
never user text, names or values, so a builder can run it on a TEST-ONLY bank.

usage: claude_sf401_panelcheck.py DIR [--part N]      DIR holds turns.jsonl, truth.jsonl, decoys.jsonl, corrections.jsonl
  --part N (1-4): check one writer's part (lives sf-t-(6N-5)..sf-t-6N) against a quarter of the minimums
  exit 0 iff every check passes
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

TURN_KEYS = {"life_id", "day", "turn_index", "user_text", "kind", "ask_type", "facts", "gold", "creative_seed_facts"}
TRUTH_KEYS = {"fact_id", "life_id", "owner", "relation", "value", "taught_turn", "valid_until_turn"}
DECOY_KEYS = {"life_id", "turn_index", "near_fact", "style", "checked_by"}
CORR_KEYS = {"life_id", "turn_index", "old_fact", "new_fact", "style"}
KINDS = {"teach", "correct", "nosave", "ask", "smalltalk", "creative", "other"}
ASK_TYPES = {"one_hop", "two_hop", "reversal", "edit", "yesno", "never_told", "partial"}
DECOY_STYLES = {"second_value", "same_value_other_person", "visit_not_move", "past_said_as_past", "plan_or_question"}
# whole-bank minimums (PANEL-SPEC.md); a part needs ceil(min / 4)
MIN_KIND = {"teach": 120, "correct": 60, "nosave": 15, "smalltalk": 30}
MIN_ASK = {"edit": 60, "one_hop": 60, "two_hop": 20, "reversal": 12, "yesno": 20, "never_told": 12}
MIN_EDIT = {"one_hop_value": 25, "two_hop": 20, "yesno": 10}
MIN_STYLE = 8          # each of correction styles 1-6
MIN_DECOYS = 30
MIN_DAY3_DAY1 = 40


def ld(p: Path) -> list:
    out = []
    for i, line in enumerate(open(p, encoding="utf-8")):
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError:
                raise SystemExit(f"{p.name}: line {i + 1} does not parse")
    return out


def main() -> int:
    d = Path(sys.argv[1])
    part = int(sys.argv[sys.argv.index("--part") + 1]) if "--part" in sys.argv else None
    q = (lambda m: -(-m // 4)) if part else (lambda m: m)
    want = {f"sf-t-{i:02d}" for i in (range(6 * part - 5, 6 * part + 1) if part else range(1, 25))}
    errs = defaultdict(list)
    turns, truth = ld(d / "turns.jsonl"), ld(d / "truth.jsonl")
    decoys, corrs = ld(d / "decoys.jsonl"), ld(d / "corrections.jsonl")
    for name, rows, keys in (("turns", turns, TURN_KEYS), ("truth", truth, TRUTH_KEYS),
                             ("decoys", decoys, DECOY_KEYS), ("corrections", corrs, CORR_KEYS)):
        for r in rows:
            if set(r) != keys:
                errs["1 keys"].append(f"{name}:{r.get('life_id')}:{r.get('turn_index', r.get('fact_id'))}")
    lives = defaultdict(list)
    for t in turns:
        lives[t["life_id"]].append(t)
    if set(lives) != want:
        errs["2 lives"].append(f"have {len(lives)} want {len(want)}; extra {len(set(lives) - want)} missing {len(want - set(lives))}")
    tk = {(t["life_id"], t["turn_index"]): t for t in turns}
    fid = {f["fact_id"]: f for f in truth}
    if len(fid) != len(truth):
        errs["2 fact ids unique"].append(str(len(truth) - len(fid)))
    for life, ts in lives.items():
        ts.sort(key=lambda t: t["turn_index"])
        if [t["turn_index"] for t in ts] != list(range(len(ts))):
            errs["2 turn_index contiguous"].append(life)
        days = [t["day"] for t in ts]
        if days != sorted(days) or set(days) != {1, 2, 3}:
            errs["2 days 1-3 in order"].append(life)
        for dd, n in Counter(days).items():
            if not 5 <= n <= 9:
                errs["2 5-9 turns per day"].append(f"{life}:day{dd}={n}")
    for t in turns:
        k = f"{t['life_id']}:{t['turn_index']}"
        if t["kind"] not in KINDS:
            errs["3 kind"].append(k)
        if (t["kind"] == "ask") != (t["ask_type"] is not None) or (t["ask_type"] and t["ask_type"] not in ASK_TYPES):
            errs["3 ask_type"].append(k)
        if (t["kind"] in ("teach", "correct")) != bool(t["facts"]):
            errs["3 facts only on teach/correct"].append(k)
        if (t["kind"] == "ask") != (t["gold"] is not None):
            errs["3 gold only on asks"].append(k)
        if not isinstance(t["user_text"], str) or not t["user_text"].strip():
            errs["3 empty text"].append(k)
        if t["creative_seed_facts"] != []:
            errs["3 no creative"].append(k)
        for f in t["facts"] or []:
            m = [x for x in truth if x["life_id"] == t["life_id"] and x["taught_turn"] == t["turn_index"]
                 and x["owner"] == f.get("owner") and x["relation"] == f.get("relation") and x["value"] == f.get("value")]
            if len(m) != 1:
                errs["9 turn fact <-> truth row (exactly one)"].append(k)
    for f in truth:
        t = tk.get((f["life_id"], f["taught_turn"]))
        if t is None or not any(x.get("owner") == f["owner"] and x.get("relation") == f["relation"]
                                and x.get("value") == f["value"] for x in (t["facts"] or [])):
            errs["9 truth row taught in its turn"].append(f["fact_id"])
    # corrections
    closed = {f["fact_id"] for f in truth if f["valid_until_turn"] is not None}
    olds, news = set(), set()
    ccount = Counter()
    for c in corrs:
        k = f"{c['life_id']}:{c['turn_index']}"
        t = tk.get((c["life_id"], c["turn_index"]))
        o, n = fid.get(c["old_fact"]), fid.get(c["new_fact"])
        if t is None or t["kind"] != "correct" or o is None or n is None:
            errs["4 correction rows"].append(k)
            continue
        if o["valid_until_turn"] != c["turn_index"] or n["taught_turn"] != c["turn_index"] \
                or o["owner"] != n["owner"] or o["taught_turn"] >= c["turn_index"]:
            errs["4 old closed / new starts at the correction, same owner"].append(k)
        if c["style"] not in (1, 2, 3, 4, 5, 6):
            errs["4 style 1-6"].append(k)
        ccount[c["style"]] += 1
        olds.add(o["fact_id"])
        news.add(n["fact_id"])
    if closed != olds:
        errs["4 closed facts == corrected olds"].append(f"closed {len(closed)} olds {len(olds)}")
    if sum(1 for t in turns if t["kind"] == "correct") != len(corrs):
        errs["4 one corrections row per correct turn"].append(f"{len(corrs)}")
    touched = olds | news
    # asks
    acount, ecount = Counter(), Counter()
    day3day1 = 0
    for t in turns:
        if t["kind"] != "ask":
            continue
        k = f"{t['life_id']}:{t['turn_index']}"
        g = t["gold"]
        if not isinstance(g, dict) or set(g) != {"values", "type", "uses_facts"}:
            errs["1 gold keys"].append(k)
            continue
        acount[t["ask_type"]] += 1
        used = [fid.get(u) for u in g["uses_facts"]]
        if any(u is None or u["life_id"] != t["life_id"] for u in used):
            errs["2 uses_facts exist in the life"].append(k)
            continue
        if any(u["taught_turn"] >= t["turn_index"] or (u["valid_until_turn"] is not None
                                                       and u["valid_until_turn"] <= t["turn_index"]) for u in used):
            errs["2 uses_facts taught before and valid at the ask"].append(k)
        typ = t["ask_type"]
        if typ == "never_told":
            if g["type"] != "idk" or g["values"]:
                errs["3 never_told gold"].append(k)
        elif g["type"] in ("yes", "no"):
            if g["values"] or typ not in ("yesno", "edit"):
                errs["3 yes/no gold"].append(k)
        else:
            if g["type"] != "value" or not g["values"]:
                errs["3 value gold"].append(k)
            pool = {u["owner"] for u in used} if typ == "reversal" else {u["value"] for u in used}
            if typ == "edit":
                pool |= {u["value"] for u in used} | {u["owner"] for u in used}
            if not all(v in pool for v in g["values"]):
                errs["3 gold values equal a used fact's value (owner for reversal)"].append(k)
        if typ == "edit":
            if not any(u["fact_id"] in news for u in used):
                errs["5 edit ask uses a replacement fact"].append(k)
            if g["type"] in ("yes", "no"):
                ecount["yesno"] += 1
            elif len(used) >= 2:
                ecount["two_hop"] += 1
            else:
                ecount["one_hop_value"] += 1
        elif typ != "never_told":
            if any(u["fact_id"] in touched for u in used):
                errs["5 non-edit ask avoids corrected facts"].append(k)
            if t["day"] == 3 and used and all(tk[(t["life_id"], u["taught_turn"])]["day"] == 1 for u in used):
                day3day1 += 1
    # decoys
    dcount = Counter()
    for x in decoys:
        k = f"{x['life_id']}:{x['turn_index']}"
        t, f, chk = tk.get((x["life_id"], x["turn_index"])), fid.get(x["near_fact"]), tk.get((x["life_id"], x["checked_by"]))
        if t is None or f is None or chk is None or t["kind"] not in ("teach", "nosave", "smalltalk"):
            errs["7 decoy rows"].append(k)
            continue
        if x["style"] not in DECOY_STYLES:
            errs["7 decoy style"].append(k)
        dcount[x["style"]] += 1
        if f["taught_turn"] >= x["turn_index"] or f["valid_until_turn"] is not None or f["fact_id"] in touched:
            errs["7 near_fact taught before, never corrected"].append(k)
        if chk["kind"] != "ask" or chk["ask_type"] == "edit" or chk["turn_index"] <= x["turn_index"] \
                or x["near_fact"] not in (chk["gold"] or {}).get("uses_facts", []):
            errs["7 checked_by is a later non-edit ask using near_fact"].append(k)
    # names: no person owner repeats across lives
    owners = defaultdict(set)
    for f in truth:
        if f["owner"] != "USER":
            owners[f["owner"].split()[0].lower()].add(f["life_id"])
    rep = [o for o, ls in owners.items() if len(ls) > 1]
    if rep:
        errs["6 owner first names repeat across lives"].append(str(len(rep)))
    # minimums
    kc = Counter(t["kind"] for t in turns)
    for k, m in MIN_KIND.items():
        if kc[k] < q(m):
            errs["6 minimum kind"].append(f"{k} {kc[k]}<{q(m)}")
    for k, m in MIN_ASK.items():
        if acount[k] < q(m):
            errs["6 minimum ask"].append(f"{k} {acount[k]}<{q(m)}")
    for k, m in MIN_EDIT.items():
        if ecount[k] < q(m):
            errs["6 minimum edit sub"].append(f"{k} {ecount[k]}<{q(m)}")
    for s in range(1, 7):
        if ccount[s] < q(MIN_STYLE):
            errs["6 minimum correction style"].append(f"{s} {ccount[s]}<{q(MIN_STYLE)}")
    if sum(dcount.values()) < q(MIN_DECOYS) or len(dcount) < (5 if not part else min(5, q(MIN_DECOYS))):
        errs["6 minimum decoys"].append(f"{sum(dcount.values())} styles {len(dcount)}")
    if day3day1 < q(MIN_DAY3_DAY1):
        errs["6 minimum day-3 asks on day-1 facts"].append(f"{day3day1}<{q(MIN_DAY3_DAY1)}")
    summary = {"lives": len(lives), "turns": len(turns), "truth": len(truth), "kinds": dict(kc),
               "asks": dict(acount), "edit_sub": dict(ecount), "correction_styles": dict(sorted(ccount.items())),
               "decoy_styles": dict(dcount), "day3_asks_on_day1_facts": day3day1,
               "errors": {k: len(v) for k, v in errs.items()}}
    print(json.dumps(summary, sort_keys=True))
    for k, v in sorted(errs.items()):
        print("FAIL", k, ":", ", ".join(v[:12]) + (" ..." if len(v) > 12 else ""))
    print("ALL CHECKS PASS" if not errs else "CHECKS FAILED")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
