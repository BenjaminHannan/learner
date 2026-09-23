#!/usr/bin/env python3
"""Exp 257 scorer = the 235b scorer's score() (claude_smolear235b_score.score, unchanged: arms
A_raw / A_brake / A / B, marks M1-M5 with the same bars) on items from the strict 257 loader
(chain_aliases on every hop; schema check -> exit 3; panel sha check -> exit 4), with the brake,
gate and relation matching pointed at relation table v2.

python claude_smolear257_score.py --panel P --a-preds A.json --b-preds B.json --tau-file TAU.json --out S.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235b_score as SC  # noqa: E402
import claude_smolear257_panel as P  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--a-preds", required=True)
    ap.add_argument("--b-preds", required=True)
    ap.add_argument("--tau-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-sha", action="store_true", help="pilot fixtures only")
    a = ap.parse_args()
    items = P.load_panel(a.panel, check_sha=not a.no_sha)
    tau = json.loads(Path(a.tau_file).read_text())["tau"]
    apd = json.loads(Path(a.a_preds).read_text(encoding="utf-8"))
    if apd["summary"].get("tau") != tau:
        raise SystemExit(f"a-preds were run with tau {apd['summary'].get('tau')}, sealed tau {tau}")
    res = SC.score(items, apd["preds"], json.loads(Path(a.b_preds).read_text()), tau)
    res["gpu_summary"] = apd["summary"]
    res["table"] = "relation_table_v2"
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(dict(tau=tau, marks=res["marks"], verdict=res["verdict"], median_ms=res["median_ms"]), indent=1))


if __name__ == "__main__":
    main()
