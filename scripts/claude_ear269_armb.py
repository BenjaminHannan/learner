#!/usr/bin/env python3
"""Exp 269 arm B -- the 138i rule reader + 228 guard (claude_smolear235_armb.run_items,
unchanged, via 235b's arm-B wrapper) on the statement items of ourpanel269,
items from the strict 269 loader.

python claude_ear269_armb.py --panel P --seal S --work DIR --out OUT.json [--no-sha]
python claude_ear269_armb.py --dev D.jsonl --work DIR --out OUT.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_armb as A235  # noqa: E402
import claude_ear269_panel as P  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=None)
    ap.add_argument("--seal", default=None)
    ap.add_argument("--dev", default=None)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-sha", action="store_true")
    a = ap.parse_args()
    if a.dev:
        items = P.load_dev(a.dev)
    else:
        items = P.load_panel(a.panel, seal=a.seal, check_sha=not a.no_sha)
    res = A235.run_items(items, a.work)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"arm B: {len(res)} statement items run")


if __name__ == "__main__":
    main()
