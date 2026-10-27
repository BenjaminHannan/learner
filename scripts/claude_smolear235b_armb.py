#!/usr/bin/env python3
"""Exp 235b arm B -- the 138i rule reader (scripts/claude_loop228_agent.py = 138i + 228 guard)
on each statement item of the 235b panel. Same runner as 235 (claude_smolear235_armb.run_items),
items from the strict 235b loader (schema check -> exit 3).

python claude_smolear235b_armb.py --panel P --work DIR --out OUT.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_armb as A235  # noqa: E402
import claude_smolear235b_panel as P  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = A235.run_items(P.load_panel(a.panel), a.work)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"arm B: {len(res)} statement items run")


if __name__ == "__main__":
    main()
