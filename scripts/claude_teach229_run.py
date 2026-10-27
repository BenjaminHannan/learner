#!/usr/bin/env python3
"""Exp 229 runner + scorer (statement panels).

run:   --agent A.py --config C.json --cases X.jsonl --work DIR --out rows.jsonl
       Each item gets a fresh daemon in DIR/<id>; optional item["setup"]
       (list of turns, or one string) is played first; then the statement.
       Row = id, reply, new triples (taught triples after minus before the
       statement), statement-turn seconds, setup replies.
score: --cases X.jsonl --base rows138i.jsonl --new rows229.jsonl --out score.json

Scoring rule (sealed):
  A new triple is RIGHT when its subject equals the gold subject, its
  value equals the gold value, and its relation is in relation_any or is a
  table alias / storage key of one of them (relation_table_v1 groups).
  Comparison: case-insensitive, whitespace collapsed, trailing "." dropped,
  one leading "the " dropped on subject and value. Gold subjects
  USER / user / me / I / my / the user all mean the notebook key USER.
  WRONG-SAVE triple = any new triple that is not RIGHT, and every new
  triple on a "nosave" item.
  Item right-save = a "save" item with >= 1 RIGHT new triple.
  Item wrong-save = an item with >= 1 WRONG-SAVE triple.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

USER_ALIASES = {"user", "me", "i", "my", "the user", "myself"}


def _n(s) -> str:
    s = " ".join(str(s or "").split()).strip().rstrip(".").strip().lower()
    if s.startswith("the "):
        s = s[4:]
    return s


def _subj(s) -> str:
    n = _n(s)
    return "user" if n in USER_ALIASES else n


def _load(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def run(args) -> int:
    import fable_marks123_all as M
    import fable_loop90_agent as L90
    _mod, dcls, _, _ = M.load_agent(args.agent)
    base = M.load_base_cfg(args.config)
    work = Path(args.work)
    out = open(args.out, "w")
    for it in _load(args.cases):
        root = work / it["id"]
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        d = M.make_daemon(dcls, base, root)
        setup = it.get("setup") or []
        if isinstance(setup, str):
            setup = [setup]
        turns = list(setup) + [it["statement"]]
        replies = []
        before = set()
        secs = None
        for j, t in enumerate(turns):
            if j == len(turns) - 1:
                before = {tuple(x) for x in L90.notebook_triples(d.loop.nb)}
            f = root / "inbox" / f"m{j:02d}.txt"
            f.write_text(t)
            t0 = time.perf_counter()
            d.process_file(f)
            dt = time.perf_counter() - t0
            replies.append((root / "outbox" / f"m{j:02d}.txt").read_text().strip())
            if j == len(turns) - 1:
                secs = dt
        after = {tuple(x) for x in L90.notebook_triples(d.loop.nb)}
        new = sorted(after - before)
        gone = sorted(before - after)
        row = {"id": it["id"], "statement": it["statement"],
               "reply": replies[-1], "setup_replies": replies[:-1],
               "new": [list(x) for x in new], "gone": [list(x) for x in gone],
               "secs": secs}
        out.write(json.dumps(row) + "\n")
        out.flush()
        print(f"{it['id']} {it['statement']!r} -> {replies[-1]!r} NEW={new}",
              flush=True)
    out.close()
    return 0


def _groups():
    from claude_loop229_agent import load_table229
    tb = load_table229()
    return tb["key2rel"]


def classify(it, row, key2rel):
    gold_rels = set()
    for r in it.get("relation_any") or []:
        k = "_".join(str(r).lower().split())
        gold_rels.add(k)
        if k in key2rel:
            gold_rels.add(("G", key2rel[k]))
    right, wrong = [], []
    for s, r, v in row["new"]:
        k = "_".join(str(r).lower().split())
        rel_ok = k in gold_rels or (k in key2rel and ("G", key2rel[k]) in gold_rels)
        ok = (it.get("expect") == "save" and rel_ok
              and _subj(s) == _subj(it.get("subject"))
              and _n(v) == _n(it.get("value")))
        (right if ok else wrong).append([s, r, v])
    return right, wrong


def score(args) -> int:
    import statistics
    key2rel = _groups()
    items = _load(args.cases)
    arms = {"138i": {r["id"]: r for r in _load(args.base)},
            "229": {r["id"]: r for r in _load(args.new)}}
    res = {"n_items": len(items),
           "n_save": sum(1 for i in items if i.get("expect") == "save"),
           "n_nosave": sum(1 for i in items if i.get("expect") != "save"),
           "arms": {}, "per_item": []}
    per = {}
    for arm, rows in arms.items():
        rs = ws_items = ws_trip = nosave_saves = 0
        for it in items:
            row = rows[it["id"]]
            right, wrong = classify(it, row, key2rel)
            per.setdefault(it["id"], {"id": it["id"], "family": it.get("family"),
                                      "expect": it.get("expect"),
                                      "statement": it["statement"]})[arm] = {
                "right": right, "wrong": wrong, "reply": row["reply"],
                "secs": row.get("secs")}
            if it.get("expect") == "save" and right:
                rs += 1
            if wrong:
                ws_items += 1
                ws_trip += len(wrong)
            if it.get("expect") != "save" and row["new"]:
                nosave_saves += 1
        res["arms"][arm] = {"right_saves": rs, "wrong_save_items": ws_items,
                            "wrong_save_triples": ws_trip,
                            "nosave_items_with_save": nosave_saves}
    new_nosave_wrong = 0
    same_when_base_saved = mism = 0
    diffs = []
    for it in items:
        p = per[it["id"]]
        b, n = arms["138i"][it["id"]], arms["229"][it["id"]]
        if it.get("expect") != "save" and n["new"] and \
                sorted(map(tuple, n["new"])) != sorted(map(tuple, b["new"])):
            new_nosave_wrong += 1
        if b["new"]:
            if sorted(map(tuple, b["new"])) == sorted(map(tuple, n["new"])):
                same_when_base_saved += 1
            else:
                mism += 1
                diffs.append(it["id"])
        res["per_item"].append(p)
    lat = [(arms["229"][i["id"]]["secs"] or 0) - (arms["138i"][i["id"]]["secs"] or 0)
           for i in items]
    res["new_wrong_on_nosave"] = new_nosave_wrong
    res["m4_base_saved_items"] = same_when_base_saved + mism
    res["m4_same_triples"] = same_when_base_saved
    res["m4_mismatch_ids"] = diffs
    res["median_added_ms"] = round(1000 * statistics.median(lat), 2) if lat else None
    fam = {}
    for it in items:
        if it.get("expect") != "save":
            continue
        f = fam.setdefault(it.get("family"), {"n": 0, "138i": 0, "229": 0})
        f["n"] += 1
        for arm in ("138i", "229"):
            if per[it["id"]][arm]["right"]:
                f[arm] += 1
    res["save_families"] = fam
    # new wrong saves: wrong triples 229 stores that 138i did not store on the same item
    nw_ids = []
    for it in items:
        bw = {tuple(x) for x in per[it["id"]]["138i"]["wrong"]}
        nw = [x for x in per[it["id"]]["229"]["wrong"] if tuple(x) not in bw]
        if nw:
            nw_ids.append(it["id"])
    res["new_wrong_save_ids_229"] = nw_ids
    res["inherited_wrong_save_ids"] = [
        it["id"] for it in items
        if per[it["id"]]["229"]["wrong"] and it["id"] not in nw_ids]
    # scoring subset: families ending in _cut are excluded (reported in save_families)
    sub = [it for it in items if not str(it.get("family") or "").endswith("_cut")]
    ss = [it for it in sub if it.get("expect") == "save"]
    res["scored_subset"] = {
        "n_items": len(sub), "n_save": len(ss),
        "right_229": sum(1 for it in ss if per[it["id"]]["229"]["right"]),
        "right_138i": sum(1 for it in ss if per[it["id"]]["138i"]["right"]),
        "new_wrong_items_229": sum(1 for it in sub if it["id"] in nw_ids),
        "cut_excluded_ids": [it["id"] for it in items if it not in sub]}
    Path(args.out).write_text(json.dumps(res, indent=1))
    a, b = res["arms"]["229"], res["arms"]["138i"]
    print(json.dumps({k: v for k, v in res.items() if k != "per_item"}, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--agent", required=True)
    r.add_argument("--config", required=True)
    r.add_argument("--cases", required=True)
    r.add_argument("--work", required=True)
    r.add_argument("--out", required=True)
    s = sub.add_parser("score")
    s.add_argument("--cases", required=True)
    s.add_argument("--base", required=True)
    s.add_argument("--new", required=True)
    s.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    return run(args) if args.cmd == "run" else score(args)


if __name__ == "__main__":
    sys.exit(main())
