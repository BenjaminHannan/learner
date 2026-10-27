#!/usr/bin/env python3
"""Experiment 167e -- T3: loop167c's sealed probe per-case vs loop167e.

Runs every row of loop167c's SEALED cases167c.json (25 rows, read-only)
through a FRESH in-process loop167e and diffs per-case against loop167c's
FROZEN probe output
(artifacts/fable-label167c-20260922/probe167c-loop167c.json, read-only):

  - stored triples identical to the frozen base stored;
  - every ask reply identical to the frozen base ask reply;
  - teach reply identical to the frozen base reply (the sealed 167c
    replies are Saved lines already spaced by 167c plus spaced answers;
    the 167e render is idempotent on all of them).

Predicted moves (in writing, before the run): NONE -- 25/25 rows
byte-identical (stored, teach reply, ask replies). Any per-case
difference fails T3 honestly.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_t3.py --out artifacts/fable-label167e-20260922/t3167e-vs167c.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)

ROOT = SCRIPTS.parent
ART167C = ROOT / "artifacts" / "fable-label167c-20260922"
ART167E = ROOT / "artifacts" / "fable-label167e-20260922"


def drive(row: dict, build_fn):
    with tempfile.TemporaryDirectory(prefix="167e_t3_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        turns = [row["teach"]] + [a["q"] for a in row.get("asks", [])]
        replies = [" ".join(loop.turn(t)) for t in turns]
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
    return replies[0], stored, replies[1:]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 167e T3 vs frozen 167c probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop167e_agent as L167E  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L167E.DEFAULT_CONFIG167E)
    build_new = lambda c: L167E.build_agent167e(dict(cfg_new, **c))  # noqa: E731
    cases = json.loads((ART167C / "cases167c.json").read_text(
        encoding="utf-8"))
    frozen = json.loads((ART167C / "probe167c-loop167c.json").read_text(
        encoding="utf-8"))
    fmap = {r["id"]: r for r in frozen["cases"]}
    t0 = time.time()
    rows = []
    for row in cases:
        base = fmap[row["id"]]
        try:
            reply, stored, ask_replies = drive(row, build_new)
        except Exception as exc:  # noqa: BLE001
            rows.append({"id": row["id"], "verdict": "HARNESS-ERROR",
                         "detail": repr(exc)})
            continue
        ok_stored = (stored == base["stored"])
        ok_reply = (reply == base["reply"])
        ok_asks = (ask_replies == [a["reply"] for a in base.get("asks", [])])
        bad_asks = [a for a, b in zip(ask_replies, base.get("asks", []))
                    if (b.get("want") and b["want"] not in (a or ""))]
        verdict = ("OK" if (ok_stored and ok_reply and ok_asks
                            and not bad_asks) else "MOVED")
        rows.append({"id": row["id"], "group": row["group"],
                      "stored_ok": ok_stored, "reply_ok": ok_reply,
                      "asks_ok": ok_asks, "reply": reply,
                      "reply_base": base["reply"], "verdict": verdict})
    wall = round(time.time() - t0, 1)
    ok_n = sum(1 for r in rows if r["verdict"] == "OK")
    moved = [r["id"] for r in rows if r["verdict"] != "OK"]
    payload = {"agent": "loop167e", "base": "probe167c-loop167c.json",
               "n": len(rows), "ok": ok_n, "moved": moved,
               "predicted_move_ids": [], "wall_seconds": wall,
               "cases": rows}
    dest = Path(args.out) if args.out else ART167E / "t3167e-vs167c.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop167e n={len(rows)} ok={ok_n} moved={moved} wall={wall}s")
    print(f"wrote {dest}")
    return 0 if ok_n == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
