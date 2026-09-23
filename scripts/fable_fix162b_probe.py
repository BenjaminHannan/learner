#!/usr/bin/env python3
"""Experiment 162b -- T1/T2 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN expectations (artifacts/fable-plural162b-20260922/cases162b.json,
76 rows), runs each case through a FRESH in-process loop162b (one teach per
plural/must-write/office/nowrite row; a short teach list per chain row),
then asks each follow-up question in the same loop. Rows flagged
identical_to_base run through a FRESH loop162 too: stored triples AND reply
must be byte-identical to the base agent.

Verdicts: OK / MISSED / WRONG-WRITE / WRONG-REPLY / ASK-FAIL / BASE-DIFF
(stored or reply differs from loop162 on an identical_to_base row) /
HARNESS-ERROR. Every seed/case reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix162b_probe.py \\
    --out artifacts/fable-plural162b-20260922/probe162b-loop162b.json
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
ART162B = ROOT / "artifacts" / "fable-plural162b-20260922"

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


def drive(row: dict, build_fn):
    """Run teaches + asks through a fresh loop. Returns (reply, stored, asks)."""
    with tempfile.TemporaryDirectory(prefix=row["id"] + "_") as tmp:
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


def run_case(row: dict, build_new, build_base) -> dict:
    t0 = time.time()
    try:
        reply, stored, ask_out = drive(row, build_new)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"],
                "verdict": "HARNESS-ERROR",
                "reply": f"NEW-CAUGHT {exc!r}",
                "seconds": round(time.time() - t0, 3)}
    base_reply, base_stored = None, None
    if row.get("identical_to_base"):
        try:
            base_reply, base_stored, _ = drive(row, build_base)
        except Exception as exc:  # noqa: BLE001
            return {"id": row["id"], "group": row["group"],
                    "verdict": "HARNESS-ERROR",
                    "reply": f"BASE-CAUGHT {exc!r}",
                    "seconds": round(time.time() - t0, 3)}
        if stored != base_stored or reply != base_reply:
            return {"id": row["id"], "group": row["group"],
                    "teaches": row.get("teaches", [row.get("teach", "")]),
                    "stored": stored, "base_stored": base_stored,
                    "reply": reply, "base_reply": base_reply,
                    "verdict": "BASE-DIFF",
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
            "teaches": row.get("teaches", [row.get("teach", "")]),
            "expect": exp, "want_reply": want_reply,
            "asks": ask_out, "stored": stored, "reply": reply,
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 162b T1/T2 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop162_agent as L162  # noqa: E402 (base agent, read-only)
    import fable_loop162b_agent as L162B  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L162B.DEFAULT_CONFIG162B)
    cfg_base = copy.deepcopy(L162.DEFAULT_CONFIG162)
    build_new = lambda c: L162B.build_agent162b(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L162.build_agent162(dict(cfg_base, **c))  # noqa: E731
    cases = json.loads((ART162B / "cases162b.json").read_text(
        encoding="utf-8"))
    t0 = time.time()
    out = [run_case(row, build_new, build_base) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    pl = [r for r, row in zip(out, cases) if row["group"] == "plural"]
    mw = [r for r, row in zip(out, cases) if row["group"] == "must-write"]
    ident = [(r, row) for r, row in zip(out, cases)
             if row.get("identical_to_base")]
    payload = {"agent": "loop162b", "cases_file": "cases162b.json",
               "wall_seconds": wall, "counts": counts,
               "plural_ok": sum(1 for r in pl if r["verdict"] == "OK"),
               "plural_n": len(pl),
               "must_write_ok": sum(1 for r in mw if r["verdict"] == "OK"),
               "must_write_n": len(mw),
               "identical_ok": sum(1 for r, _ in ident
                                   if r["verdict"] == "OK"),
               "identical_n": len(ident),
               "cases": out}
    dest = Path(args.out) if args.out else ART162B / "probe162b-loop162b.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop162b n={len(out)} counts={counts} "
          f"plural={payload['plural_ok']}/{len(pl)} "
          f"must_write={payload['must_write_ok']}/{len(mw)} "
          f"identical={payload['identical_ok']}/{len(ident)} wall={wall}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
