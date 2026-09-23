#!/usr/bin/env python3
"""Exp 270 dev scorer: score dev rows for arm A and arm 263 side by side.

Judgement rules mirror openpanel260-spec (normalise = lowercase + strip
edge punctuation/spaces): store_ok, reply_ok, junk, question_write. Traps
(nosave) are right iff the store does not change on the turn. Clean items
additionally require byte-identical replies A vs 263 on every turn.

Prints per-family tables for both arms, every move (A right / 263 wrong),
every new wrong (A wrong / 263 right), every rewrite on dev, and every
miss by id with reasons. Writes a JSON report.

Usage: python -B scripts/claude_type270_devscore.py <cases.json>
         <rowsA.json> <rows263.json> [report.json]
"""
import json
import sys
from pathlib import Path


def norm(s) -> str:
    return str(s).lower().strip().strip(" \t\n.,;:!?'\"()").strip()


def ntrip(t):
    return tuple(norm(x) for x in t)


def question_turn(c) -> bool:
    return c["turn"].rstrip().endswith("?")


def score_one(c, row):
    s_setup = {ntrip(t) for t in row["stored_after_setup"]}
    s_turn = {ntrip(t) for t in row["stored_after_turn"]}
    s_f = {ntrip(t) for t in row["stored"]}
    expect = {ntrip(t) for t in c["expect_store"]}
    junk_set = {t for t in (s_turn | s_f)
                if t not in s_setup and t not in expect}
    why = []
    if c["nosave"]:
        if s_turn != s_setup:
            why.append(f"saved {sorted(s_turn - s_setup)}")
        if question_turn(c) and s_turn != s_setup:
            why.append("question wrote")
        ok = not why
        return {"right": ok, "why": why, "junk": sorted(junk_set),
                "store_ok": s_turn == s_setup, "reply_ok": True,
                "question_write": False}
    added = s_turn - s_setup
    store_ok = expect <= s_turn and added <= expect
    if not store_ok:
        why.append(f"store added={sorted(added)} want={sorted(expect)}")
    if c["followup"]:
        scored = row["followup_reply"]
    elif question_turn(c) or c["family"] == "casual_q":
        turnrows = [r for r in row["rows"] if r["turn"] == c["turn"]]
        scored = turnrows[0]["reply"] if turnrows else ""
    else:
        turnrows = [r for r in row["rows"] if r["turn"] == c["turn"]]
        scored = turnrows[0]["reply"] if turnrows else ""
    gold = norm(c["gold"])
    reply_ok = gold == "" or gold in norm(scored)
    if not reply_ok:
        why.append(f"reply {scored!r} lacks {c['gold']!r}")
    qw = False
    if question_turn(c) and s_turn != s_setup:
        qw = True
    if c["followup"] and s_f != s_turn:
        qw = True
    if qw:
        why.append("question wrote")
    if junk_set:
        why.append(f"junk {sorted(junk_set)}")
    ok = store_ok and reply_ok and not qw and not junk_set
    return {"right": bool(ok), "why": why, "junk": sorted(junk_set),
            "store_ok": store_ok, "reply_ok": reply_ok,
            "question_write": qw}


def main(argv):
    cases = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    rows_a = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    rows_b = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
    bya = {r["id"]: r for r in rows_a}
    byb = {r["id"]: r for r in rows_b}
    res = []
    for c in cases:
        sa = score_one(c, bya[c["id"]])
        sb = score_one(c, byb[c["id"]])
        ra, rb = bya[c["id"]], byb[c["id"]]
        ident = ([r["reply"] for r in ra["rows"]]
                 == [r["reply"] for r in rb["rows"]])
        trow = [r for r in ra["rows"] if r["turn"] == c["turn"]][0]
        rw = (trow.get("rewrites") or [{}])[-1]
        res.append({"id": c["id"], "family": c["family"],
                    "a_right": sa["right"], "b_right": sb["right"],
                    "a_why": sa["why"], "b_why": sb["why"],
                    "identical": ident, "rewrite": rw.get("to"),
                    "norm_ms": rw.get("norm_ms")})
    fam: dict = {}
    for r in res:
        f = fam.setdefault(r["family"], [0, 0, 0, 0])
        f[0] += r["a_right"]
        f[1] += r["b_right"]
        f[2] += 1
    print(f"{'family':14s} {'A':>7s} {'263':>7s}")
    for k, v in fam.items():
        print(f"{k:14s} {v[0]:>3d}/{v[2]:<3d} {v[1]:>3d}/{v[2]:<3d}")
    moves = [r for r in res if r["a_right"] and not r["b_right"]]
    newwrong = [r for r in res if not r["a_right"] and r["b_right"]]
    bothwrong = [r for r in res if not r["a_right"] and not r["b_right"]]
    print(f"MOVES A-right/263-wrong: {len(moves)}")
    for r in moves:
        print("  MOVE", r["id"], r["family"], r["b_why"])
    print(f"NEWWRONG A-wrong/263-right: {len(newwrong)}")
    for r in newwrong:
        print("  NEWWRONG", r["id"], r["family"], r["a_why"])
    print(f"BOTHWRONG: {len(bothwrong)}")
    for r in bothwrong:
        print("  BOTH", r["id"], r["family"], r["a_why"])
    rws = [(r["id"], r["rewrite"]) for r in res if r["rewrite"]]
    print(f"REWRITES: {len(rws)}")
    for i, rw in rws:
        print(f"  RW {i}: {rw}")
    ms = [r["norm_ms"] for r in res if r["norm_ms"] is not None]
    ms.sort()
    med = ms[len(ms) // 2] if ms else 0
    print(f"norm_ms n={len(ms)} median={med}")
    clean = [r for r in res if r["family"] == "clean"]
    ci = sum(r["identical"] for r in clean)
    print(f"CLEAN identical: {ci}/{len(clean)}")
    for r in clean:
        if not r["identical"]:
            print("  NONIDENT", r["id"], r["rewrite"])
    if len(argv) > 4:
        Path(argv[4]).write_text(json.dumps(
            {"rows": res, "fam": fam,
             "moves": [r["id"] for r in moves],
             "newwrong": [r["id"] for r in newwrong],
             "bothwrong": [r["id"] for r in bothwrong],
             "rewrites": rws, "norm_ms_median": med,
             "clean_identical": [ci, len(clean)]}, indent=1),
            encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
