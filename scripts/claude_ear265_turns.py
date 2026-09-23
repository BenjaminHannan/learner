#!/usr/bin/env python3
"""Exp 265 -- write the turn list [{id, turn}] for the GPU run from the strict
265 loader (panel sha + schema checked; nothing else read).
python claude_ear265_turns.py --panel P --seal S --out TURNS.json [--no-sha]
python claude_ear265_turns.py --dev D.jsonl --out TURNS.json"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ear265_panel as P  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--panel", default=None)
ap.add_argument("--seal", default=None)
ap.add_argument("--dev", default=None)
ap.add_argument("--out", required=True)
ap.add_argument("--no-sha", action="store_true")
a = ap.parse_args()
if a.dev:
    items = P.load_dev(a.dev)
else:
    items = P.load_panel(a.panel, seal=a.seal, check_sha=not a.no_sha)
Path(a.out).write_text(json.dumps([dict(id=i["id"], turn=i["turn"]) for i in items], indent=1))
print(len(items), "turns")
