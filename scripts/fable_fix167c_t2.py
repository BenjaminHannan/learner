#!/usr/bin/env python3
"""Experiment 167c -- T2: loop167b's sealed probe per-case vs loop167c (Muse).

Runs every row of loop167b's SEALED cases167b.json (64 rows, read-only)
through a FRESH in-process loop167c and diffs per-case against loop167b's
FROZEN probe output (artifacts/fable-verb167b-20260922/probe167b-loop167b.json,
read-only):

  - stored triples identical to the frozen base stored;
  - every ask reply identical to the frozen base ask reply;
  - teach reply identical to the frozen base reply, EXCEPT the 11 predicted
    born rows (M16-M22, T03, T07, T11, T15) whose Saved line contains the
    underscore key place_of_birth: there the reply must equal the frozen
    reply with place_of_birth -> place of birth, byte-exactly.

Predicted moves (in writing, before the run): exactly those 11 reply texts,
nothing else. Verdicts recomputed under the spaced expectations must be OK
on all 64 rows. Any other per-case difference fails T2 honestly.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_t2.py --out artifacts/fable-label167c-20260922/t2167c-vs167b.json
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
ART167B = ROOT / "artifacts" / "fable-verb167b-20260922"
ART167C = ROOT / "artifacts" / "fable-label167c-20260922"

# Rows whose sealed 167b expect_reply contains an underscore relation key
# (enumerated by pre-seal scan of cases167b.json: the 7 mapped born rows +
# 4 tail born rows). Only these replies may move, by exactly this render.
PREDICTED_MOVE_IDS = frozenset(
    ["M16", "M17", "M18", "M19", "M20", "M21", "M22",
     "T03", "T07", "T11", "T15"])


def spaced(reply: str) -> str:
    return reply.replace("place_of_birth", "place of birth")


def drive(row: dict, build_fn):
    with tempfile.TemporaryDirectory(prefix="167c_t2_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        teaches = row.get("teaches", [row.get("teach", "")])
        replies = [" ".join(loop.turn(t)) for t in teaches]
        reply = replies[-1] if replies else ""
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        asks = row.get("asks", [])
        if row.get("ask") and not asks:
            asks = [{"q": row["ask"], "want": row.get("want")}]
        ask_out = []
        if row.get("expect") != "nowrite":
            for a in asks:
                ask_out.append({"q": a["q"], "want": a.get("want"),
                                "reply": " ".join(loop.turn(a["q"]))})
    return reply, stored, ask_out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 167c T2 vs frozen 167b probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop167c_agent as L167C  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L167C.DEFAULT_CONFIG167C)
    build_new = lambda c: L167C.build_agent167c(dict(cfg_new, **c))  # noqa: E731
    cases = json.loads((ART167B / "cases167b.json").read_text(
        encoding="utf-8"))
    frozen = json.loads((ART167B / "probe167b-loop167b.json").read_text(
        encoding="utf-8"))
    fmap = {r["id"]: r for r in frozen["cases"]}
    t0 = time.time()
    rows = []
    for row in cases:
        base = fmap[row["id"]]
        try:
            reply, stored, ask_out = drive(row, build_new)
        except Exception as exc:  # noqa: BLE001
            rows.append({"id": row["id"], "verdict": "HARNESS-ERROR",
                         "detail": repr(exc)})
            continue
        ok_stored = (stored == base["stored"])
        ok_asks = ([a["reply"] for a in ask_out]
                   == [a["reply"] for a in base.get("asks", [])])
        if row["id"] in PREDICTED_MOVE_IDS:
            ok_reply = (reply == spaced(base["reply"]))
            predicted = True
        else:
            ok_reply = (reply == base["reply"])
            predicted = False
        bad_asks = [a for a in ask_out
                    if a.get("want") and a["want"] not in (a["reply"] or "")]
        verdict = ("OK" if (ok_stored and ok_asks and ok_reply
                            and not bad_asks) else "MOVED")
        rows.append({"id": row["id"], "group": row["group"],
                     "predicted_move": predicted, "stored_ok": ok_stored,
                     "asks_ok": ok_asks, "reply_ok": ok_reply,
                     "reply": reply, "reply_base": base["reply"],
                     "verdict": verdict})
    wall = round(time.time() - t0, 1)
    ok_n = sum(1 for r in rows if r["verdict"] == "OK")
    moved = [r["id"] for r in rows if r["verdict"] != "OK"]
    unpredicted = [r["id"] for r in rows
                   if r["verdict"] != "OK"
                   or (r["predicted_move"] != (r["id"] in PREDICTED_MOVE_IDS))]
    # predicted rows must be OK too (their move is exactly the spaced render)
    payload = {"agent": "loop167c", "base": "probe167b-loop167b.json",
               "n": len(rows), "ok": ok_n, "moved": moved,
               "predicted_move_ids": sorted(PREDICTED_MOVE_IDS),
               "wall_seconds": wall, "cases": rows}
    dest = Path(args.out) if args.out else ART167C / "t2167c-vs167b.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop167c n={len(rows)} ok={ok_n} moved={moved} wall={wall}s")
    print(f"wrote {dest}")
    return 0 if ok_n == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
