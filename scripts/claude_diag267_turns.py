#!/usr/bin/env python3
"""Exp 267 -- write the turn list [{id, turn}] for the single GPU ear run from
the sealed dev set (sha checked against the dev SEAL; turn text only, order
kept). No scoring here.
python claude_diag267_turns.py --dev DEV.jsonl --seal SEAL --out TURNS.json"""
import argparse
import hashlib
import json
from pathlib import Path


def _expect_sha(seal_path):
    for ln in Path(seal_path).read_text().splitlines():
        parts = ln.strip().split()
        if len(parts) == 2 and parts[1].endswith("dev.jsonl"):
            return parts[0]
    raise SystemExit(f"no dev.jsonl line in seal {seal_path}")


ap = argparse.ArgumentParser()
ap.add_argument("--dev", required=True)
ap.add_argument("--seal", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
raw = Path(a.dev).read_bytes()
want = _expect_sha(a.seal)
if hashlib.sha256(raw).hexdigest() != want:
    raise SystemExit("DEV-SHA-MISMATCH")
rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
for r in rows:
    assert set(r) == {"id", "family", "turn", "gold", "clear", "notes"}, set(r)
Path(a.out).write_text(json.dumps(
    [dict(id=r["id"], turn=r["turn"]) for r in rows], indent=1))
print(len(rows), "turns")
