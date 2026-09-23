#!/usr/bin/env python3
"""Experiment 166b -- T1 sealed 166 probe through loop166b vs loop166 + T2 (Muse).

Reuses artifacts/fable-me166-20260922/cases166.json UNCHANGED (read-only):
every one of the 52 rows must be byte-identical through loop166b vs loop166
(stored triples AND teach replies AND every ask reply), because the 166
probe has no lowercase-then-capitalised mention and the display fix can
never fire there. T2: 0 wrong writes, 0 new entities vs loop166 on every
T1 case (entity counts equal, stored triples equal).

Verdicts: OK / BASE-DIFF / NEW-ENTITY / HARNESS-ERROR. Every seed/case
reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix166b_probe.py \\
    --out artifacts/fable-me166b-20260922/probe166b-loop166b.json
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
ART166 = ROOT / "artifacts" / "fable-me166-20260922"
ART166B = ROOT / "artifacts" / "fable-me166b-20260922"


def drive(row: dict, build_fn):
    with tempfile.TemporaryDirectory(prefix=row["id"] + "_") as tmp:
        loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        replies = [" ".join(loop.turn(t)) for t in row.get("teaches", [])]
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        n_entities = len(loop.nb.entities)
        ask_out = [{"q": a["q"], "reply": " ".join(loop.turn(a["q"]))}
                   for a in row.get("asks", [])]
    return replies, stored, n_entities, ask_out


def run_case(row: dict, build_new, build_base) -> dict:
    t0 = time.time()
    try:
        replies, stored, n_ent, ask_out = drive(row, build_new)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"],
                "verdict": "HARNESS-ERROR",
                "reply": f"NEW-CAUGHT {exc!r}",
                "seconds": round(time.time() - t0, 3)}
    try:
        b_replies, b_stored, b_ent, b_asks = drive(row, build_base)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"],
                "verdict": "HARNESS-ERROR",
                "reply": f"BASE-CAUGHT {exc!r}",
                "seconds": round(time.time() - t0, 3)}
    verdict = "OK"
    if n_ent != b_ent:
        verdict = "NEW-ENTITY"
    elif (stored != b_stored or replies != b_replies
            or [a["reply"] for a in ask_out]
            != [a["reply"] for a in b_asks]):
        verdict = "BASE-DIFF"
    return {"id": row["id"], "group": row["group"],
            "teaches": row.get("teaches", []),
            "stored": stored, "base_stored": b_stored,
            "replies": replies, "base_replies": b_replies,
            "asks": ask_out,
            "base_asks": b_asks, "verdict": verdict,
            "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 166b T1+T2 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop166_agent as L166  # noqa: E402 (base agent, read-only)
    import fable_loop166b_agent as L166B  # noqa: E402 (this experiment)
    cfg_new = copy.deepcopy(L166B.DEFAULT_CONFIG166B)
    cfg_base = copy.deepcopy(L166.DEFAULT_CONFIG166)
    build_new = lambda c: L166B.build_agent166b(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L166.build_agent166(dict(cfg_base, **c))  # noqa: E731
    cases = json.loads((ART166 / "cases166.json").read_text(
        encoding="utf-8"))
    t0 = time.time()
    out = [run_case(row, build_new, build_base) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"agent": "loop166b", "base": "loop166",
               "cases_file": "cases166.json (166 folder, unchanged)",
               "wall_seconds": wall, "counts": counts,
               "identical_ok": sum(1 for r in out if r["verdict"] == "OK"),
               "identical_n": len(out),
               "new_entities": sum(1 for r in out
                                   if r["verdict"] == "NEW-ENTITY"),
               "cases": out}
    dest = Path(args.out) if args.out else ART166B / "probe166b-loop166b.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop166b n={len(out)} counts={counts} wall={wall}s")
    print(f"wrote {dest}")
    return 0 if counts.get("OK", 0) == len(out) else 1


if __name__ == "__main__":
    sys.exit(main())
