#!/usr/bin/env python3
"""k1h: drop GLM answers that are the opencode route's own error text, before the data gate (Creative answers in chat
thread, 2026-09-27; k1h ADDENDUM-4).

Why: Ben's opencode Go plan hit its usage limit at about 00:57 UTC on 2026-09-27 while k1h-glm2 was running (the
Director, 03:06 UTC; opencode.log: "Go usage limit exceeded"). Helper v1.1 returns whatever opencode prints on a zero
exit, so a call made after the limit could come back as the route's error text instead of an answer. answers.jsonl
has no per-row time, so the rule is by content, fixed before any answer was read:
  R1  the answer contains one of ROUTE_MARKERS (case-insensitive), or starts with "Error" or "error:";
  R2  the same answer text (stripped, lower-cased, spaces collapsed) is given for 3 or more different item_ids.
A dropped row keeps its item_id with an empty answer, so claude_k1h_train.py check counts the item as "no_answer"
(a route loss, not a grade), and a later non-empty row for the same item still wins, as in check.
Prints counts only, never text.
  python3 -B scripts/claude_k1h_routefilter.py --answers IN.jsonl --out OUT.jsonl
  python3 -B scripts/claude_k1h_routefilter.py selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROUTE_MARKERS = ("usage limit", "limit exceeded", "rate limit", "opencode", "> build", "api key",
                 "providermodelnotfound", "insufficient credit", "insufficient balance", "unauthorized")
REPEAT_ITEMS = 3


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def route_rule(ans: str) -> str:
    low = _norm(ans)
    if any(m in low for m in ROUTE_MARKERS):
        return "R1_marker"
    if ans.strip().startswith("Error") or low.startswith("error:"):
        return "R1_error_start"
    return ""


def filter_rows(rows: list) -> tuple:
    by_text = {}
    for r in rows:
        if r.get("answer"):
            by_text.setdefault(_norm(r["answer"]), set()).add(r["item_id"])
    repeated = {t for t, ids in by_text.items() if len(ids) >= REPEAT_ITEMS}
    out, why, items_hit = [], Counter(), set()
    for r in rows:
        r = dict(r)
        ans = r.get("answer") or ""
        rule = ""
        if ans:
            rule = route_rule(ans) or ("R2_repeated" if _norm(ans) in repeated else "")
        if rule:
            why[rule] += 1
            items_hit.add(r["item_id"])
            r["answer"] = ""
            r["route_loss"] = rule
        out.append(r)
    stats = {"rows": len(rows), "nonempty_in": sum(1 for r in rows if r.get("answer")),
             "route_loss_rows": sum(why.values()), "by_rule": dict(why), "items_hit": len(items_hit),
             "nonempty_out": sum(1 for r in out if r.get("answer")), "repeated_texts": len(repeated)}
    return out, stats


def selftest() -> None:
    rows = [{"item_id": "a", "answer": "Here are three names: Tidewater, Loom, and Ember Street."},
            {"item_id": "b", "answer": "Error: Go usage limit exceeded"},
            {"item_id": "c", "answer": "You hit the usage limit for your plan."},
            {"item_id": "d", "answer": "Sure thing."}, {"item_id": "e", "answer": "sure  thing. "},
            {"item_id": "f", "answer": "Sure thing."},
            {"item_id": "g", "answer": ""},
            {"item_id": "h", "answer": "Error 502 while calling the model."},
            {"item_id": "b", "answer": "A later real answer for b."}]
    out, s = filter_rows(rows)
    assert [r["answer"] != "" for r in out] == [True, False, False, False, False, False, False, False, True], out
    assert s["by_rule"] == {"R1_marker": 2, "R2_repeated": 3, "R1_error_start": 1}, s
    assert s["items_hit"] == 6 and s["nonempty_in"] == 8 and s["nonempty_out"] == 2, s
    assert "Tidewater" not in json.dumps(s), "counts only"
    # two identical answers are not enough for R2
    out2, s2 = filter_rows([{"item_id": "x", "answer": "Same."}, {"item_id": "y", "answer": "Same."}])
    assert s2["route_loss_rows"] == 0
    print("k1h routefilter selftest 2/2 ok")


def main() -> None:
    if sys.argv[1:2] == ["selftest"]:
        return selftest()
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = [json.loads(x) for x in Path(a.answers).read_text(encoding="utf-8").splitlines() if x.strip()]
    out, stats = filter_rows(rows)
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
