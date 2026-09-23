#!/usr/bin/env python3
"""Exp 270b -- turns builder (dev mode, sealed).

Reads the dev jsonl, runs the 270b normaliser per item (per-item seen-names
memory from setup turns), and writes:
  TURNS.json [{id, turn}] for the BensPC ear run, two rows per item:
    <id>-raw  (arm A261b input: 261b's A exactly)
    <id>-norm (arm A input: normaliser + 261b's A)
  NORM.json {id: {raw, fixed, reason, norm_ms, setup_seen}}.

Asserts M4-by-construction on dev: every clean item passes through
byte-identical (exit 2 otherwise). Panel mode is a separate post-seal file.

python -B scripts/claude_type270b_turns.py --dev DEV.jsonl --out TURNS.json --normmanifest NORM.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_type270b_normalise as N  # noqa: E402 (THE ONE CHANGE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--normmanifest", required=True)
    a = ap.parse_args()
    items = [json.loads(x) for x in Path(a.dev).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    turns, manif = [], {}
    for it in items:
        seen: dict = {}
        for s in it.get("setup", []):
            for k, v in N.seen_names_from_text270b(s).items():
                seen.setdefault(k, v)
        fixed, reason, ms = N.normalise270b(it["turn"], seen)
        turns.append({"id": it["id"] + "-raw", "turn": it["turn"]})
        turns.append({"id": it["id"] + "-norm", "turn": fixed})
        manif[it["id"]] = {"raw": it["turn"], "fixed": fixed,
                           "reason": reason, "norm_ms": ms,
                           "setup_seen": seen,
                           "fired": fixed != it["turn"]}
        if it["family"] == "clean" and fixed != it["turn"]:
            print(f"CLEAN-FIRED (forbidden): {it['id']}: "
                  f"{it['turn']!r} -> {fixed!r}", flush=True)
            sys.exit(2)
    Path(a.out).write_text(json.dumps(turns, indent=1), encoding="utf-8")
    Path(a.normmanifest).write_text(json.dumps(manif, indent=1),
                                    encoding="utf-8")
    fired = sum(1 for v in manif.values() if v["fired"])
    print(f"{len(items)} items -> {len(turns)} turns, fired {fired}")
    byfam: dict = {}
    for it in items:
        f = byfam.setdefault(it["family"], [0, 0])
        f[1] += 1
        f[0] += manif[it["id"]]["fired"]
    for fam, (f, n) in sorted(byfam.items()):
        print(f"  {fam}: fired {f}/{n}")


if __name__ == "__main__":
    main()
