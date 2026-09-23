#!/usr/bin/env python3
"""Experiment 157 -- B1 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN cases from artifacts/fable-filler157-20260922/cases157.json
(60 cases), each through a FRESH in-process loop. Triples via
fable_loop90_agent.notebook_triples.

Groups:
  filler teach    filler text on loop157 vs bare text on loop150:
                  stored triples must be equal and non-empty.
  filler question setup teaches on both loops, then filler ask on loop157
                  vs bare ask on loop150: replies must be byte-equal and
                  contain the want answer.
  title           capitalised filler-lead, no comma, on both loops: replies
                  and stored triples must be identical, and no stored
                  subject may lose the filler word (0 wrong writes).
  same150         correction markers + filler+garbage on both loops:
                  replies and stored triples must be identical.

Verdicts per case: OK / FAIL(+reason). Every case reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix157_probe.py \\
    --out artifacts/fable-filler157-20260922/probe157-loop157.json
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
ART157 = ROOT / "artifacts" / "fable-filler157-20260922"


def run_turns(turns: list[str], build_fn) -> dict:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="p157_") as tmp:
        try:
            loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        except Exception as exc:  # noqa: BLE001
            return {"reply": f"BOOT-FAILED {exc!r}", "stored": [],
                    "seconds": round(time.time() - t0, 3)}
        try:
            replies = [" ".join(loop.turn(t)) for t in turns]
            stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        except Exception as exc:  # noqa: BLE001
            return {"reply": f"HARNESS-CAUGHT {exc!r}", "stored": [],
                    "seconds": round(time.time() - t0, 3)}
    return {"reply": replies[-1] if replies else "", "stored": stored,
            "seconds": round(time.time() - t0, 3)}


def judge(row: dict, build157, build150) -> dict:
    out = {"id": row["id"], "group": row["group"]}
    if row["group"] == "filler" and row["kind"] == "teach":
        got = run_turns([row["filler"]], build157)
        ref = run_turns([row["bare"]], build150)
        ok = (got["stored"] == ref["stored"] and len(got["stored"]) > 0)
        out.update({"filler": row["filler"], "bare": row["bare"],
                    "stored157": got["stored"], "stored150": ref["stored"],
                    "reply157": got["reply"], "reply150": ref["reply"],
                    "verdict": "OK" if ok else "FAIL:stored-mismatch",
                    "seconds": round(got["seconds"] + ref["seconds"], 3)})
    elif row["group"] == "filler" and row["kind"] == "question":
        setup = list(row.get("setup", []))
        got = run_turns(setup + [row["filler"]], build157)
        ref = run_turns(setup + [row["bare"]], build150)
        want = str(row.get("want", ""))
        ok = (got["reply"] == ref["reply"]
              and want.lower() in got["reply"].lower())
        out.update({"filler": row["filler"], "bare": row["bare"],
                    "reply157": got["reply"], "reply150": ref["reply"],
                    "want": want,
                    "verdict": "OK" if ok else "FAIL:reply-mismatch",
                    "seconds": round(got["seconds"] + ref["seconds"], 3)})
    elif row["group"] == "title":
        got = run_turns([row["text"]], build157)
        ref = run_turns([row["text"]], build150)
        lead = str(row.get("lead", "")).lower()
        stripped_write = any(
            not str(t[0]).lower().startswith(lead) for t in got["stored"]
        ) if got["stored"] else False
        ok = (got["reply"] == ref["reply"]
              and got["stored"] == ref["stored"]
              and not stripped_write)
        out.update({"text": row["text"], "stored157": got["stored"],
                    "stored150": ref["stored"], "reply157": got["reply"],
                    "reply150": ref["reply"],
                    "verdict": "OK" if ok else "FAIL:title-write-or-diff",
                    "seconds": round(got["seconds"] + ref["seconds"], 3)})
    else:  # same150
        got = run_turns([row["text"]], build157)
        ref = run_turns([row["text"]], build150)
        ok = (got["reply"] == ref["reply"]
              and got["stored"] == ref["stored"])
        out.update({"text": row["text"], "stored157": got["stored"],
                    "stored150": ref["stored"], "reply157": got["reply"],
                    "reply150": ref["reply"],
                    "verdict": "OK" if ok else "FAIL:not-identical",
                    "seconds": round(got["seconds"] + ref["seconds"], 3)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 157 B1 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop157_agent as L157  # noqa: E402 (this experiment)
    import fable_loop150_agent as L150  # noqa: E402 (base, read-only)
    cfg157 = copy.deepcopy(L157.DEFAULT_CONFIG157)
    cfg150 = copy.deepcopy(L150.DEFAULT_CONFIG150)
    build157 = lambda c: L157.build_agent157(dict(cfg157, **c))  # noqa: E731
    build150 = lambda c: L150.build_agent150(dict(cfg150, **c))  # noqa: E731
    cases = json.loads((ART157 / "cases157.json").read_text(encoding="utf-8"))
    t0 = time.time()
    out = [judge(row, build157, build150) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"agent": "loop157-vs-loop150", "cases_file": "cases157.json",
               "wall_seconds": wall, "counts": counts, "cases": out}
    dest = Path(args.out) if args.out else ART157 / "probe157-loop157.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"n={len(out)} counts={counts} wall={wall}s")
    print(f"wrote {dest}")
    return 0 if counts.get("OK", 0) == len(out) else 1


if __name__ == "__main__":
    sys.exit(main())
