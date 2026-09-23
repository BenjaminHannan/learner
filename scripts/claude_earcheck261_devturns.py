#!/usr/bin/env python3
"""Exp 261 -- dev jsonl rows -> turns list [{id, turn}] for GPU ear runs.
python claude_earcheck261_devturns.py --dev DEV.jsonl --out TURNS.json"""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--dev", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
rows = [json.loads(x) for x in Path(a.dev).read_text().splitlines() if x.strip()]
Path(a.out).write_text(json.dumps([dict(id=r["id"], turn=r["turn"]) for r in rows], indent=1))
print(len(rows), "turns")
