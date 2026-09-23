#!/usr/bin/env python3
"""Exp 230b-r scorer: M1 on the fresh blind panel, with M1(c) re-defined.

  python -B scripts/claude_namecheck230br_score.py ROWS.json OUT.json

ROWS.json = output of the UNCHANGED 230b driver:
  scripts/claude_namecheck230b_marks.py --panel --panel-dir \
      artifacts/claude-namecheckpanel230br-20260922 ROWS.json
(which runs live 230 and live 230b once each per item, fresh temp workdirs).

Marks (same as 230b except (c)):
 (a) false_yes = 0: 230b reply starts "Yes" when expect is NO, or no name
     is stored, or asked_name differs from the stored name.
 (b) every NO item whose base230 reply starts "Yes. Your name is " is now
     exactly "No. Your name is <stored>.".
 (c) every YES item with base_yes true (panel field; if absent, base230
     reply starts "Yes") still starts "Yes" on 230b. YES items with
     base_yes false are reported, not scored.
 (d) every UNCHANGED item byte-identical to its base230 reply.
 (e) question writes = 0.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_namecheck230b_score as S  # noqa: E402 (sealed 230b, read-only)

YES_PREFIX = "Yes. Your name is "


def main(rows_path: str, out_path: str) -> int:
    import claude_loop230b_agent as B
    rows = json.loads(Path(rows_path).read_text(encoding="utf-8"))
    o = {"items": len(rows), "false_yes": 0, "question_writes": 0,
         "NO_total": 0, "NO_base_yes": 0, "NO_fixed": 0,
         "YES_total": 0, "YES_base_yes": 0, "YES_kept": 0,
         "YES_base_no_reported": 0, "UNCHANGED_total": 0,
         "UNCHANGED_identical": 0, "base_file_mismatch": 0,
         "rule_ok": 0, "other_labels": {}}
    detail = []
    for r in rows:
        exp = str(r["expect"]).strip().upper()
        last = r["per"][-1]
        rep = " ".join(last["r230b"]).strip()
        live = " ".join(last["r230"]).strip()
        base = S._last_reply(r.get("base_row"))
        b = base if base is not None else live
        stored = last["stored"]
        asked = B.asked_name(last["turn"])
        fy = rep.startswith("Yes") and (
            not stored or exp == "NO"
            or (asked is not None and not B.same_name(asked, stored)))
        o["false_yes"] += int(fy)
        o["question_writes"] += sum(p["writes230b"] for p in r["per"]
                                    if p["turn"].strip().endswith("?"))
        o["rule_ok"] += int(all(p["ok"] for p in r["per"])
                            and r["facts_same"])
        o["base_file_mismatch"] += int(base is not None and base != live)
        item = r.get("item") or {}
        by = item.get("base_yes")
        if by is None:
            by = (r.get("base_row") or {}).get("base_yes")
        if by is None:
            by = b.startswith("Yes")
        note = ""
        if exp == "NO":
            o["NO_total"] += 1
            if b.startswith(YES_PREFIX):
                o["NO_base_yes"] += 1
                ok = bool(stored) and rep == B.NO_NAME_FMT % stored
                o["NO_fixed"] += int(ok)
                note = "fixed" if ok else "NOT FIXED"
            else:
                note = "base not Yes (reported)"
        elif exp == "YES":
            o["YES_total"] += 1
            if by:
                o["YES_base_yes"] += 1
                ok = rep.startswith("Yes")
                o["YES_kept"] += int(ok)
                note = "kept" if ok else "LOST YES"
            else:
                o["YES_base_no_reported"] += 1
                note = "base_yes false (reported, not scored)"
        elif exp in ("UNCHANGED", "SAME"):
            o["UNCHANGED_total"] += 1
            ok = rep == b
            o["UNCHANGED_identical"] += int(ok)
            note = "identical" if ok else "CHANGED"
        else:
            o["other_labels"][exp] = o["other_labels"].get(exp, 0) + 1
        detail.append({"id": r["id"], "expect": exp, "base_yes": bool(by),
                       "turn": last["turn"], "stored": stored,
                       "base230": base, "live230": live, "r230b": rep,
                       "moved": rep != live, "false_yes": fy, "note": note})
        print(f"{r['id']:<11} {exp:<10} {'MOVED' if rep != live else '     '}"
              f" {last['turn']!r} 230={live!r} 230b={rep!r} {note}"
              + (" FALSE-YES" if fy else ""))
    passed = {
        "a_false_yes_0": o["false_yes"] == 0,
        "b_no_fixed_all": o["NO_fixed"] == o["NO_base_yes"],
        "c_yes_kept_all_base_yes": o["YES_kept"] == o["YES_base_yes"],
        "d_unchanged_identical_all":
            o["UNCHANGED_identical"] == o["UNCHANGED_total"],
        "e_question_writes_0": o["question_writes"] == 0,
    }
    o["passed"] = passed
    o["M1_PASS"] = all(passed.values())
    Path(out_path).write_text(json.dumps({"summary": o, "detail": detail},
                                         indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(json.dumps(o))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
