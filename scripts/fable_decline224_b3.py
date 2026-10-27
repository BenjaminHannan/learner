#!/usr/bin/env python3
"""Exp 224b mark B3: loop224 sleepsmoke206 report passes the same marks as
the sealed 138i report (artifacts/fable-sleepsmoke206-20260922/s1-138i.json).

  python3 -B scripts/fable_decline224_b3.py --report <loop224 smoke json> --out <json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "artifacts" / "fable-sleepsmoke206-20260922" / "s1-138i.json"
KEYS = ("installed", "sleeps_logged", "episodes_at_install", "probes_right",
        "probes_wrong", "probes_abstain", "sleep_overwrote_taught",
        "taught_good", "taught_total", "taught_dupes")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    base = json.loads(BASE.read_text(encoding="utf-8"))
    new = json.loads(Path(a.report).read_text(encoding="utf-8"))
    rows = [{"mark": k, "138i": base.get(k), "224": new.get(k),
             "same": base.get(k) == new.get(k)} for k in KEYS]
    rows.append({"mark": "broken_chain.verdict",
                 "138i": base["broken_chain"]["verdict"],
                 "224": new["broken_chain"]["verdict"],
                 "same": base["broken_chain"]["verdict"]
                 == new["broken_chain"]["verdict"]})
    rep = {"rows": rows, "pass": all(r["same"] for r in rows),
           "agent": new.get("agent")}
    Path(a.out).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    for r in rows:
        print(f"{r['mark']:<24} 138i={r['138i']!s:<8} 224={r['224']!s:<8} {'ok' if r['same'] else 'DIFF'}")
    print("B3", "PASS" if rep["pass"] else "FAIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
