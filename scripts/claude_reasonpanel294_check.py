#!/usr/bin/env python3
"""Validator for the sealed reasonpanel294 test panel.

Checks counts, schema, id uniqueness, support fids, the structured "frame",
and mechanically re-derives gold from the notebook + frame for every
category whose answer follows from the rows by rule.

Usage: python scripts/claude_reasonpanel294_check.py [path/to/items.jsonl]
Exit code 0 = pass. Prints category-level facts only (no item content).
"""
import json
import re
import sys
from collections import Counter, defaultdict

DEFAULT = "artifacts/claude-reasonpanel294-20260923/items.jsonl"

MAIN = ["one_step", "two_step", "backwards", "yes_no", "counting", "comparing",
        "before_after", "newest_correction", "missing_fact"]
HELD = ["heldout_three_step", "heldout_big_notebook"]
EXPECTED = {**{c: 30 for c in MAIN}, **{c: 15 for c in HELD}}
KINDS = {"value", "who", "yesno", "count", "compare", "before", "after"}
KIND_OF = {
    "one_step": {"value"}, "two_step": {"value"}, "newest_correction": {"value"},
    "missing_fact": {"value"}, "backwards": {"who"}, "yes_no": {"yesno"},
    "counting": {"count"}, "comparing": {"compare"}, "before_after": {"before", "after"},
    "heldout_three_step": {"value"}, "heldout_big_notebook": {"value"},
}
ROW_RANGE = {"heldout_three_step": (8, 16), "heldout_big_notebook": (30, 40)}
# relations that may legitimately hold several values for one subject
MULTI = {"child", "speaks", "cat", "plays"}
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


class Fail(Exception):
    pass


# relations that also say something about the value person (siblings,
# friends, neighbours, cousins); a reverse row would make "X's sister" or
# "whose sister is V" ambiguous, so none may point back at a queried person
SYM = {"sister": "sib", "brother": "sib", "best_friend": "bf", "neighbor": "nb", "cousin": "cz"}


def symmetric_ok(item):
    nb, fr = item["notebook"], item["frame"]
    if fr["kind"] == "value":
        cur = fr["who"][0]
        for rel in fr["relations"]:
            rows = [r for r in nb if r["subject"] == cur and r["relation"] == rel]
            if rel in SYM:
                for r in nb:
                    if SYM.get(r["relation"]) == SYM[rel] and r["value"] == cur:
                        raise Fail("reverse symmetric row makes hop ambiguous")
            if not rows:
                return
            cur = newest(rows)["value"]
    if fr["kind"] == "who" and fr["relations"][0] in SYM:
        g, v = SYM[fr["relations"][0]], fr["value"]
        hits = [r for r in nb if SYM.get(r["relation"]) == g and v in (r["subject"], r["value"])]
        if len(hits) != 1:
            raise Fail("symmetric backwards ambiguous")


def newest(rows):
    return max(rows, key=lambda r: r["when"])


def solve(item):
    """Return (answer, support_fids_set) derived from notebook + frame."""
    nb, fr = item["notebook"], item["frame"]
    kind, who, rels, val = fr["kind"], fr["who"], fr["relations"], fr["value"]
    by = defaultdict(list)
    for r in nb:
        by[(r["subject"], r["relation"])].append(r)

    if kind == "value":
        cur, sup = who[0], set()
        for rel in rels:
            rows = by.get((cur, rel), [])
            if not rows:
                return "UNKNOWN", set()
            sup |= {r["fid"] for r in rows}
            cur = newest(rows)["value"]
        return cur, sup
    if kind == "who":
        rows = [r for r in nb if r["relation"] == rels[0] and r["value"] == val]
        subs = {r["subject"] for r in rows}
        if len(subs) != 1:
            raise Fail("backwards value not unique")
        return rows[0]["subject"], {r["fid"] for r in rows}
    if kind == "yesno":
        rows = by.get((who[0], rels[0]), [])
        if not rows:
            raise Fail("yes/no fact absent")
        r = newest(rows)
        return ("yes" if r["value"] == val else "no"), {r["fid"]}
    if kind == "count":
        rows = by.get((who[0], rels[0]), [])
        return str(len({r["value"] for r in rows})), {r["fid"] for r in rows}
    if kind == "compare":
        a, b = who
        ra, rb = by.get((a, rels[0]), []), by.get((b, rels[0]), [])
        if len(ra) != 1 or len(rb) != 1:
            raise Fail("compare rows missing/duplicated")
        va, vb = int(ra[0]["value"]), int(rb[0]["value"])
        if va == vb:
            raise Fail("compare tie")
        pick_a = (va > vb) if fr["direction"] == "more" else (va < vb)
        return (a if pick_a else b), {ra[0]["fid"], rb[0]["fid"]}
    if kind in ("before", "after"):
        rows = sorted(by.get((who[0], rels[0]), []), key=lambda r: r["year"])
        years = [r["year"] for r in rows]
        if len(set(years)) != len(years):
            raise Fail("duplicate years")
        idx = [i for i, r in enumerate(rows) if r["value"] == val]
        if len(idx) != 1:
            raise Fail("pivot not unique")
        j = idx[0] + (-1 if kind == "before" else 1)
        if j < 0 or j >= len(rows):
            raise Fail("no neighbour for pivot")
        return rows[j]["value"], {rows[idx[0]]["fid"], rows[j]["fid"]}
    raise Fail("unknown kind")


def check_item(it):
    keys = {"id", "category", "notebook", "question", "gold", "frame"}
    if set(it) != keys:
        raise Fail(f"keys {sorted(it)}")
    cat = it["category"]
    if cat not in EXPECTED:
        raise Fail("bad category")
    nb = it["notebook"]
    lo, hi = ROW_RANGE.get(cat, (4, 14))
    if not lo <= len(nb) <= hi:
        raise Fail(f"row count {len(nb)}")
    whens = []
    for i, r in enumerate(nb, 1):
        if not {"fid", "subject", "relation", "value", "when"} <= set(r) or \
                not set(r) <= {"fid", "subject", "relation", "value", "when", "year"}:
            raise Fail("row keys")
        if r["fid"] != f"f{i}":
            raise Fail("fid sequence")
        if not isinstance(r["when"], int) or ("year" in r and not isinstance(r["year"], int)):
            raise Fail("when/year type")
        if not SNAKE.match(r["relation"]):
            raise Fail("relation not snake_case")
        for k in ("subject", "value"):
            if not isinstance(r[k], str) or not r[k]:
                raise Fail("empty field")
        whens.append(r["when"])
    if len(set(whens)) != len(whens):
        raise Fail("duplicate when")
    if cat != "before_after" and any("year" in r for r in nb):
        raise Fail("year only in before_after")
    if cat == "before_after" and not any("year" in r for r in nb):
        raise Fail("before_after without year")

    # single-valued relations: one row per subject+relation, except the one
    # correction in newest_correction and year-stamped history rows
    keyc = Counter((r["subject"], r["relation"]) for r in nb
                   if r["relation"] not in MULTI and "year" not in r)
    dups = [k for k, c in keyc.items() if c > 1]
    if cat == "newest_correction":
        if len(dups) != 1 or keyc[dups[0]] != 2:
            raise Fail("correction must be exactly one duplicated key")
        vals = {r["value"] for r in nb if (r["subject"], r["relation"]) == dups[0]}
        if len(vals) != 2:
            raise Fail("correction values equal")
    elif dups:
        raise Fail("unexpected duplicate subject+relation")

    fr = it["frame"]
    if set(fr) != {"kind", "who", "relations", "value", "direction"}:
        raise Fail("frame keys")
    if fr["kind"] not in KINDS or fr["kind"] not in KIND_OF[cat]:
        raise Fail("frame kind")
    rels_present = {r["relation"] for r in nb}
    for k, rel in enumerate(fr["relations"]):
        last = k == len(fr["relations"]) - 1
        if rel not in rels_present and not (cat == "missing_fact" and last):
            raise Fail("frame relation not in notebook")
        if not SNAKE.match(rel):
            raise Fail("frame relation not snake_case")
    q = it["question"]
    for name in fr["who"]:
        if name not in q:
            raise Fail("frame who not in question")
    if fr["value"] is not None and fr["value"].lower() not in q.lower():
        raise Fail("frame value not in question")
    if (fr["direction"] is not None) != (fr["kind"] == "compare"):
        raise Fail("direction")
    if fr["direction"] not in (None, "more", "less"):
        raise Fail("direction value")
    nhops = {"one_step": 1, "two_step": 2, "heldout_three_step": 3}
    if cat in nhops and len(fr["relations"]) != nhops[cat]:
        raise Fail("hop count")
    if cat == "heldout_big_notebook" and len(fr["relations"]) not in (1, 2):
        raise Fail("big notebook hop count")
    if fr["kind"] == "compare" and len(fr["who"]) != 2:
        raise Fail("compare needs two names")

    gold = it["gold"]
    if set(gold) != {"answer", "support"}:
        raise Fail("gold keys")
    fids = {r["fid"] for r in nb}
    if not set(gold["support"]) <= fids:
        raise Fail("support fid missing")
    if cat == "missing_fact":
        if gold["answer"] != "UNKNOWN" or gold["support"]:
            raise Fail("missing_fact gold")
    elif gold["answer"] == "UNKNOWN":
        raise Fail("UNKNOWN outside missing_fact")

    symmetric_ok(it)
    ans, sup = solve(it)
    if ans != gold["answer"]:
        raise Fail("re-derived answer differs")
    if sup != set(gold["support"]):
        raise Fail("re-derived support differs")
    if cat == "counting" and not ans.isdigit():
        raise Fail("count not integer")
    distract = len(fids) - len(set(gold["support"]))
    if distract < 2:
        raise Fail("fewer than 2 distractor rows")
    if cat == "missing_fact":
        # a tempting near miss at the failing hop: the same relation for
        # someone else, and the same person with some other relation
        by = defaultdict(list)
        for r in nb:
            by[(r["subject"], r["relation"])].append(r)
        cur = fr["who"][0]
        for rel in fr["relations"]:
            rows = by.get((cur, rel))
            if not rows:
                break
            cur = newest(rows)["value"]
        if not any(r["relation"] == rel for r in nb):
            raise Fail("missing_fact lacks other-person near miss")
        if not any(r["subject"] == cur for r in nb):
            raise Fail("missing_fact lacks same-person near miss")
    return cat, ans


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    items = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    errs, cats, yn = [], Counter(), Counter()
    ids = [it.get("id") for it in items]
    if len(items) != 300:
        errs.append(f"expected 300 items, got {len(items)}")
    if len(set(ids)) != len(ids):
        errs.append("duplicate ids")
    if sorted(ids) != [f"rp294-{i:03d}" for i in range(1, 301)]:
        errs.append("ids not rp294-001..300")
    for it in items:
        try:
            cat, ans = check_item(it)
            cats[cat] += 1
            if cat == "yes_no":
                yn[ans] += 1
        except (Fail, KeyError, TypeError, ValueError, IndexError) as e:
            errs.append(f"{it.get('id')}: {type(e).__name__}: {e}")
    for c, n in EXPECTED.items():
        if cats[c] != n:
            errs.append(f"category {c}: {cats[c]} != {n}")
    # categories must be interleaved, not grouped: longest same-category run
    run = best = 1
    for a, b in zip(items, items[1:]):
        run = run + 1 if a["category"] == b["category"] else 1
        best = max(best, run)
    if best > 4:
        errs.append(f"categories look grouped (run of {best})")
    if yn and abs(yn["yes"] - yn["no"]) > 4:
        errs.append(f"yes/no imbalance {dict(yn)}")
    for c in list(EXPECTED):
        print(f"{c:22s} {cats[c]}")
    print(f"yes_no split: yes={yn['yes']} no={yn['no']}")
    if errs:
        print("FAIL")
        for e in errs[:50]:
            print(" ", e)
        sys.exit(1)
    print(f"PASS: {len(items)} items")


if __name__ == "__main__":
    main()
