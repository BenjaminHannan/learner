#!/usr/bin/env python3
"""Exp 236 scorer: loop236 rows vs loop221 rows on the same case file.

Rows come from scripts/claude_fullname232_run.py (one JSON line per item:
{"id", "turns": [{"turn","reply","ms","is_question","active","all"}]}).
Cases: JSONL with id, family, setup, question, gold (list or null).

Families and what counts as right:
  unique_first, of_form : every gold value appears in the reply
  ambiguous             : reply starts "Which <T> do you mean:" and names every
                          gold candidate; no stored value appears
  exact_wins            : every gold value appears in the reply
  no_match, last_name_only : reply byte-identical to 221
  statement(s)          : reply byte-identical to 221 AND identical active and
                          all-taught triples after the turn
Global: wrong value = the reply contains a stored value (active triples after
the turn) that is not a gold value (ambiguous: any stored value);
question write = the question turn changed the all-taught list.
Added time = median over question turns of (236 ms - 221 ms), paired by id.

Usage: python -B scripts/claude_firstname236_score.py CASES ROWS236 ROWS221 OUT.json
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8")
            .splitlines() if x.strip()]


def fam_of(case) -> str:
    f = str(case.get("family", ""))
    return "statement" if f in ("statement", "statements") else f


def has(reply: str, v: str) -> bool:
    return re.search(r"(?<![\w-])" + re.escape(v.strip().rstrip("."))
                     + r"(?![\w-])", reply) is not None


def main(argv) -> int:
    cases = {c["id"]: c for c in load(argv[1])}
    r236 = {r["id"]: r for r in load(argv[2])}
    r221 = {r["id"]: r for r in load(argv[3])}
    out = {"items": [], "by_family": {}}
    wrong = qwrites = 0
    deltas = []
    for cid, case in cases.items():
        fam = fam_of(case)
        a, b = r236[cid]["turns"], r221[cid]["turns"]
        last, base = a[-1], b[-1]
        prev_all = a[-2]["all"] if len(a) > 1 else []
        gold = case.get("gold") or []
        if isinstance(gold, str):
            gold = [g.strip() for g in gold.split(";") if g.strip()]
        reply = last["reply"]
        stored_vals = {str(t[2]) for t in last["active"]}
        is_q = fam != "statement"
        if fam in ("ambiguous",):
            bad = [v for v in stored_vals if has(reply, v)]
        else:
            bad = [v for v in stored_vals if has(reply, v)
                   and not any(v.lower() == g.lower() for g in gold)
                   and fam in ("unique_first", "of_form", "exact_wins")]
        wrong += len(bad) > 0
        qw = is_q and sorted(map(tuple, last["all"])) != sorted(
            map(tuple, prev_all))
        qwrites += bool(qw)
        if fam in ("unique_first", "of_form", "exact_wins"):
            ok = bool(gold) and all(has(reply, g) for g in gold) and not bad
        elif fam == "ambiguous":
            ok = (reply.startswith("Which ") and " do you mean:" in reply
                  and all(has(reply, g) for g in gold) and not bad)
        elif fam in ("no_match", "last_name_only"):
            ok = reply == base["reply"]
        elif fam == "statement":
            ok = (reply == base["reply"]
                  and sorted(map(tuple, last["active"])) == sorted(
                      map(tuple, base["active"]))
                  and sorted(map(tuple, last["all"])) == sorted(
                      map(tuple, base["all"])))
        else:
            ok = None
        # earlier (setup) turns must match 221 byte for byte
        setup_same = all(x["reply"] == y["reply"] for x, y in
                         zip(a[:-1], b[:-1]))
        if is_q:
            deltas.append(last["ms"] - base["ms"])
        fb = out["by_family"].setdefault(fam, {"n": 0, "right": 0})
        fb["n"] += 1
        fb["right"] += bool(ok)
        out["items"].append({"id": cid, "family": fam,
                             "question": case.get("question"),
                             "reply236": reply, "reply221": base["reply"],
                             "right": ok, "wrong_values": bad,
                             "question_write": bool(qw),
                             "setup_same_as_221": setup_same,
                             "moved": reply != base["reply"]})
    out["wrong_values"] = wrong
    out["question_writes"] = qwrites
    out["median_added_ms"] = statistics.median(deltas) if deltas else None
    out["n"] = len(cases)
    Path(argv[4]).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                             encoding="utf-8")
    for it in out["items"]:
        print(f"{it['id']} {it['family']:<15} right={it['right']} "
              f"moved={it['moved']} setup_same={it['setup_same_as_221']} "
              f"| {it['question']!r} -> {it['reply236']!r} "
              f"(221: {it['reply221']!r})")
    print("by_family", json.dumps(out["by_family"]))
    print(f"wrong_values={wrong} question_writes={qwrites} "
          f"median_added_ms={out['median_added_ms']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
