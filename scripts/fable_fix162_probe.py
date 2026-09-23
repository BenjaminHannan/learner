#!/usr/bin/env python3
"""Experiment 162 -- T1/T2 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN expectations (artifacts/fable-thename162-20260922/cases162.json),
runs each case through a FRESH in-process loop162 (one teach per must-write /
office / nowrite row; a short teach list per chain row), then asks each
follow-up question in the same loop. Judges the FULL triple(s), every ask
answer, and (for nowrite/office rows) the reply kind or exact frozen reply.

Verdicts: OK / MISSED (expected write, got none) / WRONG-WRITE (any stored
triple outside the expectation) / WRONG-REPLY (no write, but a nowrite case
got the wrong clarify kind or a non-matching frozen reply) / ASK-FAIL
(triple exact, but a follow-up ask does not answer V) / HARNESS-ERROR.
Every seed/case reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix162_probe.py \\
    --out artifacts/fable-thename162-20260922/probe162-loop162.json
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
ART162 = ROOT / "artifacts" / "fable-thename162-20260922"

SPLIT_MARK = "one fact at a time"
HEARSAY_MARK = "hear it somewhere"
DIDNT_MARK = "didn't understand"
ONEWORD_MARK = "one-word names"
SAVED_MARK = "Saved:"


def reply_ok(kind: str | None, reply: str, frozen: str | None = None) -> bool:
    if frozen is not None:
        return reply == frozen
    if kind in (None, "any"):
        return True
    if kind == "split":
        return SPLIT_MARK in reply
    if kind == "hearsay":
        return HEARSAY_MARK in reply
    if kind == "didnt":
        return DIDNT_MARK in reply
    if kind == "oneword":
        return ONEWORD_MARK in reply
    if kind == "saved":
        return SAVED_MARK in reply
    return True


def run_case(row: dict, build_fn) -> dict:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix=row["id"] + "_") as tmp:
        try:
            loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "verdict": "HARNESS-ERROR",
                    "reply": f"BOOT-FAILED {exc!r}",
                    "seconds": round(time.time() - t0, 3)}
        try:
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
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "verdict": "HARNESS-ERROR",
                    "reply": f"HARNESS-CAUGHT {exc!r}",
                    "seconds": round(time.time() - t0, 3)}
    exp = row["expect"]
    want_reply = row.get("reply", "any")
    frozen = row.get("frozen_reply")
    verdict = None
    if isinstance(exp, dict) and "base" in exp:
        want = [list(t) for t in exp["base"]]
        if stored != want:
            verdict = "WRONG-WRITE"
        elif not reply_ok(want_reply, reply, frozen):
            verdict = "WRONG-REPLY"
        else:
            verdict = "OK"
    elif exp == "nowrite":
        if stored:
            verdict = "WRONG-WRITE"
        elif reply_ok(want_reply, reply, frozen):
            verdict = "OK"
        else:
            verdict = "WRONG-REPLY"
    else:
        if isinstance(exp, list) and exp and isinstance(exp[0], list):
            want = [list(t) for t in exp]
        else:
            want = [list(exp)]
        if stored == want:
            bad = [a for a in ask_out
                   if a.get("want") and a["want"] not in (a["reply"] or "")]
            if bad:
                verdict = "ASK-FAIL"
            elif not reply_ok(want_reply, reply, frozen):
                verdict = "WRONG-REPLY"
            else:
                verdict = "OK"
        elif not stored:
            verdict = "MISSED"
        else:
            verdict = "WRONG-WRITE"
    return {"id": row["id"], "group": row["group"],
            "teaches": teaches, "expect": exp, "want_reply": want_reply,
            "asks": ask_out, "stored": stored, "reply": reply,
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 162 T1/T2 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop162_agent as L162  # noqa: E402 (this experiment)
    cfg = copy.deepcopy(L162.DEFAULT_CONFIG162)
    build_fn = lambda c: L162.build_agent162(dict(cfg, **c))  # noqa: E731
    cases = json.loads((ART162 / "cases162.json").read_text(encoding="utf-8"))
    t0 = time.time()
    out = [run_case(row, build_fn) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    mw = [r for r, row in zip(out, cases) if row["group"] == "must-write"]
    mw_ok = sum(1 for r in mw if r["verdict"] == "OK")
    payload = {"agent": "loop162", "cases_file": "cases162.json",
               "wall_seconds": wall, "counts": counts,
               "must_write_ok": mw_ok, "must_write_n": len(mw),
               "cases": out}
    dest = Path(args.out) if args.out else ART162 / "probe162-loop162.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop162 n={len(out)} counts={counts} "
          f"must_write={mw_ok}/{len(mw)} wall={wall}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
