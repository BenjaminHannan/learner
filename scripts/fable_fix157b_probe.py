#!/usr/bin/env python3
"""Experiment 157b -- T1 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN cases from artifacts/fable-filler157b-20260922/cases157b.json
(60 cases), each through a FRESH in-process loop. Triples via
fable_loop90_agent.notebook_triples.

Groups (new loop157b vs base loop157):
  cap teach     capitalised/stacked filler text on loop157b vs bare twin
                on loop157: stored triples must be equal and non-empty,
                replies byte-equal.
  cap question  setup teaches on both loops, then filler ask on loop157b
                vs bare ask on loop157: replies byte-equal, want present.
  title         filler-word-initial titles on both loops: replies and
                stored triples identical, 0 stripped-subject writes.
  same157       garbage/correction/hedge on both loops: replies and stored
                triples identical.

Verdicts per case: OK / FAIL(+reason). Every case reported, never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix157b_probe.py \\
    --out artifacts/fable-filler157b-20260922/probe157b-loop157b.json
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
ART157B = ROOT / "artifacts" / "fable-filler157b-20260922"


def run_turns(turns: list[str], build_fn) -> dict:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="p157b_") as tmp:
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


def judge(row: dict, build_new, build_base) -> dict:
    out = {"id": row["id"], "group": row["group"]}
    if row["group"] == "cap" and row["kind"] == "teach":
        got = run_turns([row["filler"]], build_new)
        ref = run_turns([row["bare"]], build_base)
        ok = (got["stored"] == ref["stored"] and len(got["stored"]) > 0
              and got["reply"] == ref["reply"])
        out.update({"filler": row["filler"], "bare": row["bare"],
                    "stored157b": got["stored"], "stored157": ref["stored"],
                    "reply157b": got["reply"], "reply157": ref["reply"],
                    "verdict": "OK" if ok else "FAIL:stored-or-reply-mismatch",
                    "seconds": round(got["seconds"] + ref["seconds"], 3)})
    elif row["group"] == "cap" and row["kind"] == "question":
        setup = list(row.get("setup", []))
        got = run_turns(setup + [row["filler"]], build_new)
        ref = run_turns(setup + [row["bare"]], build_base)
        want = str(row.get("want", ""))
        ok = (got["reply"] == ref["reply"]
              and want.lower() in got["reply"].lower())
        out.update({"filler": row["filler"], "bare": row["bare"],
                    "reply157b": got["reply"], "reply157": ref["reply"],
                    "want": want,
                    "verdict": "OK" if ok else "FAIL:reply-mismatch",
                    "seconds": round(got["seconds"] + ref["seconds"], 3)})
    elif row["group"] == "title":
        got = run_turns([row["text"]], build_new)
        ref = run_turns([row["text"]], build_base)
        lead = str(row.get("lead", "")).lower()
        stripped_write = any(
            not str(t[0]).lower().startswith(lead) for t in got["stored"]
        ) if got["stored"] else False
        ok = (got["reply"] == ref["reply"]
              and got["stored"] == ref["stored"]
              and not stripped_write)
        out.update({"text": row["text"], "stored157b": got["stored"],
                    "stored157": ref["stored"], "reply157b": got["reply"],
                    "reply157": ref["reply"],
                    "verdict": "OK" if ok else "FAIL:title-write-or-diff",
                    "seconds": round(got["seconds"] + ref["seconds"], 3)})
    else:  # same157
        got = run_turns([row["text"]], build_new)
        ref = run_turns([row["text"]], build_base)
        ok = (got["reply"] == ref["reply"]
              and got["stored"] == ref["stored"])
        out.update({"text": row["text"], "stored157b": got["stored"],
                    "stored157": ref["stored"], "reply157b": got["reply"],
                    "reply157": ref["reply"],
                    "verdict": "OK" if ok else "FAIL:not-identical",
                    "seconds": round(got["seconds"] + ref["seconds"], 3)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 157b T1 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop157b_agent as L157B  # noqa: E402 (this experiment)
    import fable_loop157_agent as L157  # noqa: E402 (base, read-only)
    cfg_new = copy.deepcopy(L157B.DEFAULT_CONFIG157B)
    cfg_base = copy.deepcopy(L157.DEFAULT_CONFIG157)
    build_new = lambda c: L157B.build_agent157b(dict(cfg_new, **c))  # noqa: E731
    build_base = lambda c: L157.build_agent157(dict(cfg_base, **c))  # noqa: E731
    cases = json.loads((ART157B / "cases157b.json").read_text(encoding="utf-8"))
    t0 = time.time()
    out = [judge(row, build_new, build_base) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"agent": "loop157b-vs-loop157", "cases_file": "cases157b.json",
               "wall_seconds": wall, "counts": counts, "cases": out}
    dest = Path(args.out) if args.out else ART157B / "probe157b-loop157b.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"n={len(out)} counts={counts} wall={wall}s")
    print(f"wrote {dest}")
    return 0 if counts.get("OK", 0) == len(out) else 1


if __name__ == "__main__":
    sys.exit(main())
