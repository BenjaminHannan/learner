#!/usr/bin/env python3
"""Experiment 156 -- T1 sealed probe runner (Muse). Read-only vs repo.

Reads FROZEN expectations from
artifacts/fable-smalltalk156-20260922/cases156.json (68 cases: 44
small-talk, 24 near-miss), one message each through a FRESH in-process
loop. Small-talk rows run on loop156: expect 0 writes and the exact
fixed class reply. Near-miss rows run on loop156 AND loop150 (fresh
each): expect byte-identical replies and identical stored triples.

Verdicts: OK / WRONG-WRITE / WRONG-REPLY / NEAR-DIFF (near-miss reply
or stored triples differ from loop150). Every case reported, never
averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix156_probe.py \\
    --out artifacts/fable-smalltalk156-20260922/probe156-loop156.json
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

import fable_fix156_smalltalk as S156  # noqa: E402 (replies, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)

ROOT = SCRIPTS.parent
ART156 = ROOT / "artifacts" / "fable-smalltalk156-20260922"


def fresh_turn(build_fn, text: str) -> dict:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="t1_") as tmp:
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
    ap = argparse.ArgumentParser(description="Exp 156 T1 probe")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    import fable_loop150_agent as L150  # noqa: E402 (base, read-only)
    import fable_loop156_agent as L156  # noqa: E402 (this experiment)
    cfg150 = copy.deepcopy(L150.DEFAULT_CONFIG150)
    cfg156 = copy.deepcopy(L156.DEFAULT_CONFIG156)
    build150 = lambda c: L150.build_agent150(dict(cfg150, **c))  # noqa: E731
    build156 = lambda c: L156.build_agent156(dict(cfg156, **c))  # noqa: E731

    cases = json.loads((ART156 / "cases156.json").read_text(encoding="utf-8"))
    t0 = time.time()
    out = []
    for row in cases:
        got = fresh_turn(build156, row["text"])
        rec = {"id": row["id"], "group": row["group"], "kind": row["kind"],
               "text": row["text"], "stored": got["stored"],
               "reply": got["reply"], "seconds": got["seconds"]}
        if row["kind"] == "smalltalk":
            want = S156.CLASS_REPLIES[{"greeting": "greeting",
                                       "thanks": "thanks", "ack": "ack",
                                       "bye": "bye"}[row["group"]]]
            rec["want_reply"] = want
            if got["stored"]:
                rec["verdict"] = "WRONG-WRITE"
            elif got["reply"] == want:
                rec["verdict"] = "OK"
            else:
                rec["verdict"] = "WRONG-REPLY"
        else:
            base = fresh_turn(build150, row["text"])
            rec["loop150_reply"] = base["reply"]
            rec["loop150_stored"] = base["stored"]
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
    payload = {"agent": "loop156", "cases_file": "cases156.json",
               "wall_seconds": wall, "counts": counts, "cases": out}
    dest = Path(args.out) if args.out else ART156 / "probe156-loop156.json"
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"agent=loop156 n={len(out)} counts={counts} wall={wall}s")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
