#!/usr/bin/env python3
"""Validator for the sealed reasonpanel296 test panel (messy, realistic notebooks).

Checks counts, schema, ids, category interleaving, the structured "frame",
and mechanically re-derives the gold answer and support set of every item
from its notebook + frame.

Usage: python scripts/claude_reasonpanel296_check.py [path/to/items.jsonl]
Exit code 0 = pass. Prints category-level facts only (no item content).
"""
import json
import re
import sys
from collections import Counter, defaultdict

DEFAULT = "artifacts/claude-reasonpanel296-20260924/items.jsonl"
PREFIX = "rp296"

CATS = ["one_step", "two_step", "backwards", "yes_no", "counting", "comparing",
        "before_after", "newest_correction", "missing_fact", "heldout_three_step"]
EXPECTED = {c: 30 for c in CATS}
KINDS = {"value", "who", "yesno", "count", "compare", "before", "after"}
KIND_OF = {
    "one_step": {"value"}, "two_step": {"value"}, "newest_correction": {"value"},
    "missing_fact": {"value"}, "backwards": {"who"}, "yes_no": {"yesno"},
    "counting": {"count"}, "comparing": {"compare"}, "before_after": {"before", "after"},
    "heldout_three_step": {"value"},
}
ROWS_MIN, ROWS_MAX = 3, 40
# relations that may hold several values for one person (never on a
# deciding path except in counting)
MULTI = {"kid", "pet", "speaks", "plays_instrument", "plays_sport", "hobby", "allergy",
         "houseplant", "visited_country", "takes_class", "volunteers_at", "subscribes_to"}
# relations that describe both people; they never appear in a frame and
# never touch a person the question depends on
SYM = {"roommate", "cousin", "sibling", "best_friend", "neighbor", "spouse", "bandmate",
       "coworker", "classmate", "friend"}
# year-stamped history relations (before_after only)
HIST = {"lived_in", "worked_at", "had_job", "drove", "played_for", "studied_at", "rented_from"}
MIN_DISTINCT_RELATIONS = 40
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


class Fail(Exception):
    pass


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
            if len({r["value"] for r in rows}) > 1 and len({r["when"] for r in rows}) != len(rows):
                raise Fail("hop has tied rows")
            sup |= {r["fid"] for r in rows}
            cur = newest(rows)["value"]
        return cur, sup
    if kind == "who":
        rows = [r for r in nb if r["relation"] == rels[0] and r["value"] == val]
        if len(rows) != 1:
            raise Fail("backwards value not unique")
        return rows[0]["subject"], {rows[0]["fid"]}
    if kind == "yesno":
        rows = by.get((who[0], rels[0]), [])
        if not rows:
            raise Fail("yes/no fact absent")
        if len(rows) != 1:
            raise Fail("yes/no fact duplicated")
        r = rows[0]
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
        rows = by.get((who[0], rels[0]), [])
        if not 2 <= len(rows) <= 4 or any("year" not in r for r in rows):
            raise Fail("history needs 2-4 year rows")
        rows = sorted(rows, key=lambda r: r["year"])
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
    if not ROWS_MIN <= len(nb) <= ROWS_MAX:
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
        if r["subject"] == r["value"]:
            raise Fail("row points at itself")
        if ("year" in r) != (r["relation"] in HIST):
            raise Fail("year exactly on history relations")
        whens.append(r["when"])
    if len(set(whens)) != len(whens):
        raise Fail("duplicate when")
    if cat != "before_after" and any("year" in r for r in nb):
        raise Fail("year only in before_after")
    if cat == "before_after" and not any("year" in r for r in nb):
        raise Fail("before_after without year")

    # single-valued relations: one row per subject+relation, except the one
    # correction in newest_correction
    keyc = Counter((r["subject"], r["relation"]) for r in nb
                   if r["relation"] not in MULTI and r["relation"] not in HIST)
    dups = [k for k, c in keyc.items() if c > 1]
    newer_first = False
    if cat == "newest_correction":
        if len(dups) != 1 or keyc[dups[0]] != 2:
            raise Fail("correction must be exactly one duplicated key")
        pair = [r for r in nb if (r["subject"], r["relation"]) == dups[0]]
        if pair[0]["value"] == pair[1]["value"]:
            raise Fail("correction values equal")
        newer_first = pair[0]["when"] > pair[1]["when"]
    elif dups:
        raise Fail("unexpected duplicate subject+relation")
    for (s, rel), c in Counter((r["subject"], r["relation"]) for r in nb if r["relation"] in HIST).items():
        yrs = [r["year"] for r in nb if (r["subject"], r["relation"]) == (s, rel)]
        if len(set(yrs)) != len(yrs):
            raise Fail("history years repeat")

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
        if rel in SYM:
            raise Fail("symmetric relation in frame")
        if rel in MULTI and cat != "counting":
            raise Fail("multi-valued relation on a deciding path")
        if rel in HIST and cat != "before_after":
            raise Fail("history relation outside before_after")
    if cat == "counting" and fr["relations"][0] not in MULTI:
        raise Fail("counting needs a multi-valued relation")
    if cat == "before_after" and fr["relations"][0] not in HIST:
        raise Fail("before_after needs a history relation")
    q = it["question"]
    if not q.endswith("?"):
        raise Fail("question mark")
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
    if cat in ("newest_correction", "missing_fact") and not 1 <= len(fr["relations"]) <= 3:
        raise Fail("hop count")
    if fr["kind"] in ("who", "yesno", "count", "compare", "before", "after") and len(fr["relations"]) != 1:
        raise Fail("one relation expected")
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

    ans, sup = solve(it)
    if ans != gold["answer"]:
        raise Fail("re-derived answer differs")
    if sup != set(gold["support"]):
        raise Fail("re-derived support differs")
    if cat == "newest_correction":
        dup_fids = {r["fid"] for r in nb if (r["subject"], r["relation"]) == dups[0]}
        if not dup_fids <= sup:
            raise Fail("correction not on the answer path")
    if cat == "counting" and not (ans.isdigit() and 1 <= int(ans) <= 7):
        raise Fail("count outside 1-7")
    if len(fids) - len(sup) < 2:
        raise Fail("fewer than 2 distractor rows")

    # people the question depends on: named people, the given value, and
    # everyone in a support row; no symmetric row may touch them
    dep = set(fr["who"]) | ({fr["value"]} if fr["value"] else set()) | {ans}
    for r in nb:
        if r["fid"] in sup:
            dep |= {r["subject"], r["value"]}
    if cat == "missing_fact":
        cur = fr["who"][0]
        by = defaultdict(list)
        for r in nb:
            by[(r["subject"], r["relation"])].append(r)
        for rel in fr["relations"]:
            dep.add(cur)
            rows = by.get((cur, rel))
            if not rows:
                break
            cur = newest(rows)["value"]
        dep.add(cur)
        # tempting near misses at the failing hop
        if not any(r["relation"] == rel for r in nb):
            raise Fail("missing_fact lacks other-person near miss")
        if not any(r["subject"] == cur for r in nb):
            raise Fail("missing_fact lacks same-person near miss")
        if rel in ("job", "workplace") and any(
                r["subject"] == cur and r["relation"] in ("job", "workplace") for r in nb):
            raise Fail("missing job/workplace is inferable from the other")
    for r in nb:
        if r["relation"] in SYM and (r["subject"] in dep or r["value"] in dep):
            raise Fail("symmetric row touches a question person")
    return cat, ans, newer_first


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    items = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    errs, cats, yn, ba, nf = [], Counter(), Counter(), Counter(), 0
    sizes = defaultdict(list)
    rels = set()
    ids = [it.get("id") for it in items]
    if len(items) != 300:
        errs.append(f"expected 300 items, got {len(items)}")
    if sorted(ids) != [f"{PREFIX}-{i:03d}" for i in range(1, 301)] or ids != sorted(ids):
        errs.append(f"ids not {PREFIX}-001..300 in order")
    for it in items:
        try:
            cat, ans, newer_first = check_item(it)
            cats[cat] += 1
            sizes[cat].append(len(it["notebook"]))
            rels |= {r["relation"] for r in it["notebook"]}
            if cat == "yes_no":
                yn[ans] += 1
            if cat == "before_after":
                ba[it["frame"]["kind"]] += 1
            nf += newer_first
        except (Fail, KeyError, TypeError, ValueError, IndexError) as e:
            errs.append(f"{it.get('id')}: {type(e).__name__}: {e}")
    for c, n in EXPECTED.items():
        if cats[c] != n:
            errs.append(f"category {c}: {cats[c]} != {n}")
    run = best = 1
    for a, b in zip(items, items[1:]):
        run = run + 1 if a["category"] == b["category"] else 1
        best = max(best, run)
    if best > 2:
        errs.append(f"more than 2 in a row share a category (run of {best})")
    if yn["yes"] != 15 or yn["no"] != 15:
        errs.append(f"yes/no split {dict(yn)}")
    if ba["before"] != 15 or ba["after"] != 15:
        errs.append(f"before/after split {dict(ba)}")
    if nf < 10:
        errs.append(f"only {nf} corrections list the newer row first")
    if len(rels) < MIN_DISTINCT_RELATIONS:
        errs.append(f"only {len(rels)} distinct relations")
    for c in CATS:
        s = sizes[c] or [0]
        print(f"{c:20s} {cats[c]:3d}  rows {min(s)}-{max(s)}")
    print(f"yes_no split: yes={yn['yes']} no={yn['no']}; before/after: {ba['before']}/{ba['after']}; "
          f"corrections newer-first: {nf}; distinct relations: {len(rels)}")
    if errs:
        print("FAIL")
        for e in errs[:50]:
            print(" ", e)
        sys.exit(1)
    print(f"PASS: {len(items)} items")


if __name__ == "__main__":
    main()
