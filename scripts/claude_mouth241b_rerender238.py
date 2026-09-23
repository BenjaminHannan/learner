#!/usr/bin/env python3
"""Exp 241b report-only: re-render 238's harvest through stage A v2
(copy of 241's post-seal script with the 241b paths).

REPORT-ONLY; changes no mark. 238's harvest.jsonl is read only
to re-render it here.

Each harvest row is one distinct reply string (possibly several lines) with
its occurrence counts. Every line goes through the sealed render_line with no
notebook records and no notebook names (the harvest has none). Because of
that, lines whose parse-back needs records (e.g. multi-value answers) may
pass through unchanged here although they would render in a live run.

Output: artifacts/claude-mouth241b-20260922/rerender238.jsonl
  {reply, rerender, changed, lines: [{route, act, why}], count, scope_count}
plus a summary printed and written to rerender238-summary.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_loop241b_agent as A241B  # noqa: E402 (sealed render path)

REPO = SCRIPTS.parent
SRC = REPO / "artifacts/claude-grammar238-20260922/harvest.jsonl"
OUT = REPO / "artifacts/claude-mouth241b-20260922"


def main() -> int:
    rows = [json.loads(x) for x in SRC.read_text(encoding="utf-8").splitlines()
            if x.strip()]
    routes, routes_w, acts_changed, acts_changed_w = (Counter(), Counter(),
                                                      Counter(), Counter())
    sev1 = []
    n_changed = w_changed = w_total = 0
    with open(OUT / "rerender238.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            reply = r["reply"]
            outs, info = [], []
            for line in reply.split("\n"):
                res = A241B.render_line(line, [], ())
                outs.append(res["text"])
                info.append({"route": res["route"], "act": res["act"],
                             "why": res.get("why")})
                routes[res["route"]] += 1
                routes_w[res["route"]] += r["count"]
                if res["route"] == "A" and res["text"] != line:
                    acts_changed[res["act"]] += 1
                    acts_changed_w[res["act"]] += r["count"]
                if res["route"] == "legacy":
                    sev1.append((res["act"], line))
            new = "\n".join(outs)
            ch = new != reply
            n_changed += ch
            w_changed += r["count"] * ch
            w_total += r["count"]
            fh.write(json.dumps({"reply": reply, "rerender": new,
                                 "changed": ch, "lines": info,
                                 "count": r["count"],
                                 "scope_count": r.get("scope_count")},
                                ensure_ascii=False) + "\n")
    summ = {"distinct_replies": len(rows), "changed_distinct": n_changed,
            "occurrences": w_total, "changed_occurrences": w_changed,
            "line_routes": dict(routes), "line_routes_by_count": dict(routes_w),
            "changed_lines_by_act": dict(acts_changed),
            "changed_lines_by_act_by_count": dict(acts_changed_w),
            "sev1_legacy_lines": len(sev1)}
    (OUT / "rerender238-summary.json").write_text(
        json.dumps(summ, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summ, indent=1))
    for a, line in sev1[:30]:
        print("  SEV1", a, line[:120])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
