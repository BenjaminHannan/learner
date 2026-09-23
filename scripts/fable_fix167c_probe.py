#!/usr/bin/env python3
"""Experiment 167c -- T1 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN expectations (artifacts/fable-label167c-20260922/cases167c.json,
25 rows: 16 ALLOWED_KEYS underscore relations + 1 verb-phrase born + 8
general FakeEars underscore relations, all fictional names). Each row runs
through a FRESH in-process loop167c (temp state dir) AND a FRESH in-process
loop167b for the same turns:

  - teach reply must equal expect_reply EXACTLY (byte-identical spaced
    Saved line, hand-checked before the seal);
  - stored triples must equal expect;
  - every ask reply must contain its want;
  - NO reply (teach or ask) may contain an underscore relation-key token
    ([a-z]+(_[a-z0-9]+)+ outside loop167c's own file/agent names -- of
    which there are none in replies);
  - notebook events must be identical between the 167c and 167b runs after
    dropping the volatile event_id (uuid hex) and prev hash-chain fields,
    which are random per run by construction (Listening._eid uuid4).

Verdicts: OK / MISSED / WRONG-WRITE / WRONG-REPLY / ASK-FAIL /
EVENT-DIFF / UNDERSCORE-LEAK / HARNESS-ERROR. Every case reported, never
averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_probe.py --out artifacts/fable-label167c-20260922/probe167c-loop167c.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
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

UNDER = re.compile(r"[a-z]+(?:_[a-z0-9]+)+")

VOLATILE_EVENT_KEYS = ("event_id", "prev")


def scrub_events(events: list[dict]) -> list[dict]:
    return [{k: v for k, v in e.items() if k not in VOLATILE_EVENT_KEYS}
            for e in events]


def drive(turns: list[str], build_fn):
    with tempfile.TemporaryDirectory(prefix="167c_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        replies = [" ".join(loop.turn(t)) for t in turns]
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        events = scrub_events(list(loop.nb.events))
    return replies, stored, events


def run_case(row: dict, build_new, build_base) -> dict:
    t0 = time.time()
    turns = [row["teach"]] + [a["q"] for a in row.get("asks", [])]
    try:
        replies, stored, events = drive(turns, build_new)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"],
                "verdict": "HARNESS-ERROR",
                "reply": f"NEW-CAUGHT {exc!r}",
                "seconds": round(time.time() - t0, 3)}
    try:
        replies_b, stored_b, events_b = drive(turns, build_base)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"],
                "verdict": "HARNESS-ERROR",
                "reply": f"BASE-CAUGHT {exc!r}",
                "seconds": round(time.time() - t0, 3)}
    reply, ask_replies = replies[0], replies[1:]
    out = {"id": row["id"], "group": row["group"], "key": row.get("key"),
           "teach": row["teach"], "stored": stored, "stored_base": stored_b,
           "reply": reply, "reply_base": replies_b[0],
           "asks": [{"q": a["q"], "want": a.get("want"), "reply": r}
                    for a, r in zip(row.get("asks", []), ask_replies)],
           "seconds": round(time.time() - t0, 3)}
    leaks = [r for r in replies if UNDER.search(r)]
    if leaks:
        out["verdict"] = "UNDERSCORE-LEAK"
        return out
    if events != events_b:
        out["verdict"] = "EVENT-DIFF"
        return out
    want = [list(row["expect"])]
    if stored != want:
        out["verdict"] = "MISSED" if not stored else "WRONG-WRITE"
        return out
    bad = [a for a in out["asks"]
           if a.get("want") and a["want"] not in (a["reply"] or "")]
    if bad:
        out["verdict"] = "ASK-FAIL"
        return out
    if reply != row.get("expect_reply"):
        out["verdict"] = "WRONG-REPLY"
        return out
    out["verdict"] = "OK"
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 167c T1 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop167b_agent as L167B  # noqa: E402 (base, read-only)
    import fable_loop167c_agent as L167C  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L167C.DEFAULT_CONFIG167C)
    cfg_base = copy.deepcopy(L167B.DEFAULT_CONFIG167B)
    build_new = lambda c: L167C.build_agent167c(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L167B.build_agent167b(dict(cfg_base, **c))  # noqa: E731
    cases = json.loads((ART167C / "cases167c.json").read_text(
        encoding="utf-8"))
    t0 = time.time()
    out = [run_case(row, build_new, build_base) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    by_group: dict[str, list] = {}
    for r, row in zip(out, cases):
        by_group.setdefault(row["group"], []).append(r)
    summary = {g: {"ok": sum(1 for r in rs if r["verdict"] == "OK"),
                   "n": len(rs)} for g, rs in by_group.items()}
    payload = {"agent": "loop167c", "cases_file": "cases167c.json",
               "wall_seconds": wall, "counts": counts,
               "by_group": summary, "cases": out}
    dest = Path(args.out) if args.out else ART167C / "probe167c-loop167c.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop167c n={len(out)} counts={counts} "
          f"groups={summary} wall={wall}s")
    print(f"wrote {dest}")
    return 0 if counts.get("OK", 0) == len(out) else 1


if __name__ == "__main__":
    sys.exit(main())
