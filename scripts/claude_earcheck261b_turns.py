#!/usr/bin/env python3
"""Exp 261b -- write the turn list [{id, turn}] for the GPU run from the strict
261b loader (panel sha + schema checked; nothing else read).
python claude_earcheck261b_turns.py --panel P --seal S --out TURNS.json [--no-sha]"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_earcheck261b_panel as P  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--panel", required=True)
ap.add_argument("--seal", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--no-sha", action="store_true")
a = ap.parse_args()
items = P.load_panel(a.panel, seal=a.seal, check_sha=not a.no_sha)
Path(a.out).write_text(json.dumps([dict(id=i["id"], turn=i["turn"]) for i in items], indent=1))
print(len(items), "turns")
