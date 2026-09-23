#!/usr/bin/env python3
"""Exp 281b dev scorer (mechanical counts only).

  dev <cases.json> <run281.json> <run281b.json> <out.json>
    stored_*  : 281b must answer with the target value, 0 writes on the
                question turn. 281's reply shown beside (dev info only).
    notstored : both arms must abstain (dontknow/clarify/save-shape-error),
                0 writes; 281b must equal 281 byte-identical.
    ambiguous : every 281b reply must equal 281's (route preserved).
    control   : every 281b reply must equal 281's.
    expect_store checked exactly when given. Question-turn writes fail.
    Never prints item text beyond ids and counts.
"""

import json
import sys

DONTKNOW = ("don't know", "do not know", "never told me",
            "never taught me", "no record", "not someone i can look up")
CLARIFY = ("could you say it another way", "didn't understand",
           "don't understand", "was that a question",
           "i only know current facts", "couldn't save that as a fact",
           "don't know that shape")


def low(s):
    return " ".join(str(s).lower().split())


def is_abstain(reply):
    r = low(reply)
    return any(m in r for m in DONTKNOW) or any(m in r for m in CLARIFY)


def is_question(turn):
    return str(turn).rstrip().endswith("?")


def main(argv):
    args = list(argv[1:])
    if args and args[0] == "dev":
        args = args[1:]
    cases = json.load(open(args[0]))
    run281 = json.load(open(args[1]))
    run281b = json.load(open(args[2]))
    outp = args[3]
    r81 = {c["id"]: c for c in run281}
    r8b = {c["id"]: c for c in run281b}
    fams = {}
    moves = []
    problems = []

    def famd(fam):
        return fams.setdefault(fam, {"n": 0, "right": 0, "miss": []})

    for c in cases:
        fam = c["family"]
        f = famd(fam)
        f["n"] += 1
        a = r81[c["id"]]["rows"]
        b = r8b[c["id"]]["rows"]
        ok = True
        for i, (ra, rb) in enumerate(zip(a, b)):
            if ra["reply"] != rb["reply"]:
                moves.append((c["id"], i))
            for row, arm in ((ra, "281"), (rb, "281b")):
                if is_question(row.get("turn", "")) and row.get("ev", 0):
                    problems.append(f"{c['id']} turn{i} {arm} question write")
                    ok = False
        if c["expect_store"] is not None:
            got = [list(t) for t in r8b[c["id"]]["stored"]]
            if sorted(got) != sorted(c["expect_store"]):
                problems.append(f"{c['id']} store {got} != {c['expect_store']}")
                ok = False
        if fam.startswith("stored") or fam == "opener_casual":
            for idx, how, text in c["checks"]:
                rep = b[idx]["reply"] if idx < len(b) else ""
                has = text in rep
                if (how == "has" and not has) or \
                        (how == "not" and has):
                    problems.append(f"{c['id']} check {idx} {how} {text!r}")
                    ok = False
            if b[-1].get("ev", 0):
                problems.append(f"{c['id']} scored turn wrote")
                ok = False
        elif fam == "notstored":
            for row in b:
                if not is_abstain(row["reply"]) or row.get("ev", 0):
                    problems.append(f"{c['id']} notstored not-abstain")
                    ok = False
                    break
            for i, (ra, rb) in enumerate(zip(a, b)):
                if ra["reply"] != rb["reply"]:
                    problems.append(f"{c['id']} turn{i} moved "
                                    f"{ra['reply'][:40]!r} -> {rb['reply'][:40]!r}")
                    ok = False
        elif fam in ("ambiguous", "control"):
            for i, (ra, rb) in enumerate(zip(a, b)):
                if ra["reply"] != rb["reply"]:
                    problems.append(f"{c['id']} turn{i} moved "
                                    f"{ra['reply'][:40]!r} -> {rb['reply'][:40]!r}")
                    ok = False
        if ok:
            f["right"] += 1
        else:
            f["miss"].append(c["id"])
    res = {"families": fams, "moves_281_to_281b": moves,
           "problems": problems}
    json.dump(res, open(outp, "w"), indent=1)
    for fam, f in res["families"].items():
        print(f"{fam:14s} {f['right']}/{f['n']} miss={f['miss']}")
    print("moves 281->281b:", len(res["moves_281_to_281b"]))
    for m in res["moves_281_to_281b"][:60]:
        print("  MOVE", m[0], m[1])
    print("problems:", res["problems"] if res["problems"] else "none")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
