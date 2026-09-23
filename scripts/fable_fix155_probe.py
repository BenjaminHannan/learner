#!/usr/bin/env python3
"""Experiment 155 -- I1/I2 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN expectations (artifacts/fable-inverted155-20260922/cases155.json
for --agent loop155, cases155x135.json for --agent loop155x135), one teach
message each through a FRESH in-process loop; must-write cases then ask
"Who is X's R?" in the same loop. Judges the FULL triple, the ask answer,
and (for nowrite/base cases) the reply kind or exact frozen reply.

Verdicts: OK / MISSED (expected write, got none) / WRONG-WRITE (any stored
triple outside the expectation) / WRONG-REPLY (no write, but a nowrite case
got the wrong clarify kind or a non-matching frozen reply) / ASK-FAIL
(triple exact, but the follow-up ask does not answer V) / HARNESS-ERROR.
Every seed/case reported, never averaged.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix155_probe.py --agent loop155 \\
    --out artifacts/fable-inverted155-20260922/probe155-loop155.json
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix155_probe.py --agent loop155x135 \\
    --out artifacts/fable-inverted155-20260922/probe155-loop155x135.json
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
ART155 = ROOT / "artifacts" / "fable-inverted155-20260922"

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
            reply = " ".join(loop.turn(row["teach"]))
            stored = [list(t) for t in L90.notebook_triples(loop.nb)]
            ask_reply = None
            if row.get("ask") and row["expect"] not in ("nowrite",):
                if not isinstance(row["expect"], dict):
                    ask_reply = " ".join(loop.turn(row["ask"]))
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
        want = [list(exp)]
        if stored == want:
            if row.get("ask") and row.get("want"):
                if row["want"] in (ask_reply or ""):
                    verdict = "OK"
                else:
                    verdict = "ASK-FAIL"
            else:
                verdict = "OK"
        elif not stored:
            verdict = "MISSED"
        else:
            verdict = "WRONG-WRITE"
    return {"id": row["id"], "group": row["group"],
            "frame": row.get("frame"), "teach": row["teach"],
            "expect": exp, "want_reply": want_reply,
            "ask": row.get("ask"), "want": row.get("want"),
            "stored": stored, "reply": reply, "ask_reply": ask_reply,
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 155 I1/I2 probe")
    ap.add_argument("--agent", default="loop155",
                    choices=("loop155", "loop155x135"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    if args.agent == "loop155":
        import fable_loop155_agent as L155  # noqa: E402 (this experiment)
        cfg = copy.deepcopy(L155.DEFAULT_CONFIG155)
        build_fn = lambda c: L155.build_agent155(dict(cfg, **c))  # noqa: E731
        cases_name = "cases155.json"
    else:
        import fable_loop155_agent as L155  # noqa: E402 (this experiment)
        cfg = copy.deepcopy(L155.DEFAULT_CONFIG155X135)
        build_fn = lambda c: L155.build_agent155x135(dict(cfg, **c))  # noqa: E731
        cases_name = "cases155x135.json"
    cases = json.loads((ART155 / cases_name).read_text(encoding="utf-8"))
    t0 = time.time()
    out = [run_case(row, build_fn) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    mw = [r for r, row in zip(out, cases) if row["group"] == "must-write"]
    mw_ok = sum(1 for r in mw if r["verdict"] == "OK")
    payload = {"agent": args.agent, "cases_file": cases_name,
               "wall_seconds": wall, "counts": counts,
               "must_write_ok": mw_ok, "must_write_n": len(mw),
               "cases": out}
    dest = Path(args.out) if args.out else ART155 / f"probe155-{args.agent}.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent={args.agent} n={len(out)} counts={counts} "
          f"must_write={mw_ok}/{len(mw)} wall={wall}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
