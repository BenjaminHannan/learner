#!/usr/bin/env python3
"""Exp 261 -- report-only arm A on the known 257 panel (run once, never tuned).

Loads earpanel257 with 257's own strict loader (sha + schema; exits 3/4 there),
runs the SEALED 261 arm assembly + checker split at the sealed theta on GPU ear
preds + recorded prompt-B pYES, and prints arm A / A_brake / A_gate / A_raw /
A_nocanon M1-M4 next to B from 257's sealed run/b_preds.json. No verdict, no
tuning, report only.

python claude_earcheck261_score257.py --a-preds A.json --pyes Y.json --theta TH --out O.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_panel as P7  # noqa: E402
import claude_earcheck261_scoremain as SM  # noqa: E402

PANEL = "artifacts/claude-earpanel257-20260922/panel.jsonl"
BPREDS = "artifacts/claude-smolear257-20260922/run/b_preds.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a-preds", required=True)
    ap.add_argument("--pyes", nargs="+", required=True)
    ap.add_argument("--theta", type=float, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    items = P7.load_panel(PANEL)  # sealed 257 sha + schema
    apd = json.loads(Path(a.a_preds).read_text(encoding="utf-8"))
    pmap = {}
    for path in a.pyes:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        for cid, v in d["checks"].items():
            pmap[cid] = (float(v["p"]), float(v.get("ms", 0.0)))
    res = SM.score(items, apd["preds"], json.loads(Path(BPREDS).read_text()),
                   pmap, a.theta)
    res["gpu_summary"] = apd["summary"]
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    for arm in SM.ARMS:
        m = res["marks"][arm]
        print(arm, "M1:", m["M1_no_save_saved"], "M2:", m["M2_wrong_saves"],
              "M3:", f"{m['M3_hit']}/{m['M3_gold']}", m["M3_recall_pct"],
              "M4:", m.get("M4_hit"), m.get("M4_gold"), m.get("M4_recall_pct"),
              "M3b:", m.get("M3b_unsure"), m.get("M3b_unsure_pct"))
    print("median_ms:", res["median_ms"], "p90:", res["p90_ms"], "max:", res["max_ms"],
          "m6_mismatch:", res["m6_mismatch"])


if __name__ == "__main__":
    main()
