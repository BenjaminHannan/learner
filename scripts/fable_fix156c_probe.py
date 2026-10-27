#!/usr/bin/env python3
"""Experiment 156c -- S1/S2 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN expectations from
artifacts/fable-smalltalk156c-20260922/cases156c.json (77 cases: 44
new small-talk in 5 classes, 33 near-misses), one message each through
a FRESH in-process loop. Small-talk rows run on loop156c: expect 0
writes and the exact fixed class reply. Near-miss rows run on loop156c
AND loop138h (fresh each): expect byte-identical replies and identical
stored triples.

Verdicts: OK / WRONG-WRITE / WRONG-REPLY / NEAR-DIFF (near-miss reply
or stored triples differ from loop138h). Every case reported, never
averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix156c_probe.py \\
    --out artifacts/fable-smalltalk156c-20260922/probe156c-loop156c.json
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

import fable_fix156c_smalltalk as S156c  # noqa: E402 (replies, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)

ROOT = SCRIPTS.parent
ART156c = ROOT / "artifacts" / "fable-smalltalk156c-20260922"


def fresh_turn(build_fn, text: str) -> dict:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="t156c_") as tmp:
        try:
            loop = build_fn({"state_dir": tmp, "sleep_threshold": 100000})
        except Exception as exc:  # noqa: BLE001
            return {"reply": f"BOOT-FAILED {exc!r}", "stored": [],
                    "seconds": round(time.time() - t0, 3)}
        try:
            reply = " ".join(loop.turn(text))
            stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        except Exception as exc:  # noqa: BLE001
            return {"reply": f"HARNESS-CAUGHT {exc!r}", "stored": [],
                    "seconds": round(time.time() - t0, 3)}
    return {"reply": reply, "stored": stored,
            "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 156c S1/S2 probe")
    ap.add_argument("--out", default=None)
    ap.add_argument("--cases", default=None)
    args = ap.parse_args(argv)
    import fable_loop138h_agent as L138H  # noqa: E402 (base, read-only)
    import fable_loop156c_agent as L156c  # noqa: E402 (this experiment)
    cfg138 = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
    cfg156c = copy.deepcopy(L156c.DEFAULT_CONFIG156c)
    build138 = lambda c: L138H.build_agent138h(  # noqa: E731
        dict(cfg138, **c))
    build156c = lambda c: L156c.build_agent156c(  # noqa: E731
        dict(cfg156c, **c))

    cases = json.loads(Path(args.cases or (ART156c / "cases156c.json"))
                       .read_text(encoding="utf-8"))
    t0 = time.time()
    out = []
    for row in cases:
        got = fresh_turn(build156c, row["text"])
        rec = {"id": row["id"], "group": row["group"], "kind": row["kind"],
               "text": row["text"], "stored": got["stored"],
               "reply": got["reply"], "seconds": got["seconds"]}
        if row["kind"] == "smalltalk":
            want = S156c.CLASS_REPLIES[row["group"]]
            rec["want_reply"] = want
            if got["stored"]:
                rec["verdict"] = "WRONG-WRITE"
            elif got["reply"] == want:
                rec["verdict"] = "OK"
            else:
                rec["verdict"] = "WRONG-REPLY"
        else:
            base = fresh_turn(build138, row["text"])
            rec["loop138h_reply"] = base["reply"]
            rec["loop138h_stored"] = base["stored"]
            if (got["reply"] == base["reply"]
                    and got["stored"] == base["stored"]):
                rec["verdict"] = "OK"
            else:
                rec["verdict"] = "NEAR-DIFF"
        out.append(rec)
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {"agent": "loop156c", "cases_file": "cases156c.json",
               "wall_seconds": wall, "counts": counts, "cases": out}
    dest = Path(args.out) if args.out else ART156c / "probe156c-loop156c.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop156c n={len(out)} counts={counts} wall={wall}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
