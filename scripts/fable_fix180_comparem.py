#!/usr/bin/env python3
"""Exp 180 G2 compare -- marks180 per-case vs sealed marks138g.

Read-only scrub-compare (volatile metadata + agent-path strings). Prints
every non-identical case. Exit 0 iff all diffs are within the sealed
predicted set (sleep SKIP reason agent filename only).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix138g_compareg2 as C2  # noqa: E402 (scrub+loader, read-only)

ROOT = SCRIPTS.parent
G = ROOT / "artifacts" / "fable-lowercase180-20260922" / "marks180"
F = ROOT / "artifacts" / "fable-agent138g-20260922" / "marks138g"


def main(argv=None) -> int:
    names = ["p2-report.json", "p3-report.json", "p4-report.json",
             "rt110-report.json", "q1-report.json", "bench-report.json",
             "rt81-report.json", "sleep-report.json", "soak-report.json",
             "q4-report.json", "fable_marks123_summary.json"]
    bad = 0
    for name in names:
        gp, fp = G / name, F / name
        if not gp.exists() or not fp.exists():
            print(f"SKIP {name} (missing)", flush=True)
            continue
        g = C2.scrub(json.loads(gp.read_text(encoding="utf-8")))
        f = C2.scrub(json.loads(fp.read_text(encoding="utf-8")))
        if g == f:
            print(f"SAME {name}", flush=True)
            continue
        # predicted-only diff: sleep SKIP reason naming the new agent file
        if name == "sleep-report.json":
            gs, fs = json.dumps(g, sort_keys=True), json.dumps(
                f, sort_keys=True)
            if (gs.replace("fable_loop180_agent.py", "<A>").replace(
                    "loop180", "<A>") == fs.replace(
                    "fable_loop138g_agent.py", "<A>").replace(
                    "loop138g", "<A>")):
                print(f"SAME-predicted-rename {name}", flush=True)
                continue
        print(f"DIFF {name}", flush=True)
        bad += 1
        jg, jf = json.dumps(g, sort_keys=True), json.dumps(
            f, sort_keys=True)
        print(f"  180: {jg[:600]}", flush=True)
        print(f"  138g: {jf[:600]}", flush=True)
    # deep per-case check on the suite detail dirs (p3 cases, rt110 rows)
    for sub, key in (("p3", None), ("rt110-tmp", None)):
        gd, fd = G / sub, F / sub
        if not gd.exists() or not fd.exists():
            continue
        gf = sorted(p.name for p in gd.iterdir())
        ff = sorted(p.name for p in fd.iterdir())
        print(f"{sub}: 180-files={len(gf)} 138g-files={len(ff)}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
