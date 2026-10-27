#!/usr/bin/env python3
"""Exp 257 arm B -- the 138i rule reader + 228 guard (claude_smolear235_armb.run_items, unchanged)
on the statement items of ear panel 257, items from the strict 257 loader.

python claude_smolear257_armb.py --panel P --work DIR --out OUT.json [--no-sha]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_armb as A235  # noqa: E402
import claude_smolear257_panel as P  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-sha", action="store_true")
    a = ap.parse_args()
    res = A235.run_items(P.load_panel(a.panel, check_sha=not a.no_sha), a.work)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"arm B: {len(res)} statement items run")


if __name__ == "__main__":
    main()
