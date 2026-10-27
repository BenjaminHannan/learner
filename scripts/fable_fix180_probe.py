#!/usr/bin/env python3
"""Exp 180 T1 -- sealed lowercase case file through loop180 vs loop138g.

Reads artifacts/fable-lowercase180-20260922/case180.json (sealed). Runs
the dialogue on a fresh loop180 and the twin dialogue on a fresh
loop138g, checking per-turn:
  - cap      : replies byte-identical 180 vs 138g (setup parity)
  - ask      : 180 reply == 138g twin reply
  - teach    : 180 replies "Did you mean: <twin>?", 0 notebook writes;
               then "yes" -> 180 reply == 138g twin reply and the fact
               delta == twin's fact delta
  - trap     : same turn on both loops, replies byte-identical
Exits 0 iff every check passes. Prints one line per turn (never averaged).

Run (Mac CPU, offline; only AFTER PASSMARKS.md + case file are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix180_probe.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop138g_agent as L138G  # noqa: E402 (base, read-only)
import fable_loop180_agent as L180  # noqa: E402 (agent under test, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-lowercase180-20260922"


def triples(loop) -> list[list[str]]:
    return sorted([list(t) for t in L90.notebook_triples(loop.nb)])


def fresh(which: str):
    tmp = tempfile.mkdtemp(prefix=f"loop180-t1-{which}-")
    if which == "180":
        return L180.build_agent180({"state_dir": tmp,
                                    "sleep_threshold": 100000})
    return L138G.build_agent138g({"state_dir": tmp,
                                  "sleep_threshold": 100000})


def main(argv=None) -> int:
    t0 = time.time()
    case_path = ART / "case180.json"
    steps = json.loads(case_path.read_text(encoding="utf-8"))
    loop180 = fresh("180")
    loop138 = fresh("138g")
    fails: list[dict] = []
    counts = {"cap": 0, "ask": 0, "teach": 0, "trap": 0}

    def turn(loop, text: str) -> str:
        return " ".join(loop.turn(text))

    for s in steps:
        kind = s["kind"]
        if kind == "cap":
            r180, r138 = turn(loop180, s["turn"]), turn(loop138, s["turn"])
            ok = r180 == r138
            detail = f"180={r180!r} 138g={r138!r}"
        elif kind == "ask":
            r180, r138 = turn(loop180, s["turn"]), turn(loop138, s["twin"])
            ok = r180 == r138
            detail = f"180={r180!r} twin={r138!r}"
        elif kind == "teach":
            before = triples(loop180)
            r180 = turn(loop180, s["turn"])
            nowrites = triples(loop180) == before
            want_confirm = "Did you mean: %s?" % s["twin"].rstrip().rstrip(
                ".?!")
            r_twin = turn(loop138, s["twin"])
            r_yes = turn(loop180, "yes")
            # Dialogues stay in lockstep: the full triple sets must match
            # after the commit (commit events == twin's events exactly).
            twin_events_ok = (sorted(triples(loop180))
                              == sorted(triples(loop138)))
            ok = (r180 == want_confirm and nowrites and r_yes == r_twin
                  and twin_events_ok)
            detail = (f"confirm={r180!r} want={want_confirm!r} "
                      f"nowrites={nowrites} yes={r_yes!r} twin={r_twin!r} "
                      f"events_ok={twin_events_ok}")
        elif kind == "trap":
            r180, r138 = turn(loop180, s["turn"]), turn(loop138, s["turn"])
            ok = r180 == r138
            detail = f"180={r180!r} 138g={r138!r}"
        else:
            fails.append({"id": s.get("id"), "err": "bad-kind"})
            continue
        counts[kind] += 1
        print(f"{'OK ' if ok else 'FAIL'} {s.get('id')} [{kind}] "
              f"{s['turn']!r} :: {detail}", flush=True)
        if not ok:
            fails.append({"id": s.get("id"), "kind": kind,
                          "turn": s["turn"], "detail": detail})

    # 0 new WRONG-ish / junk writes on T1: any write whose triple uses a
    # lowercase surface form of a known name, or any write on ask/trap.
    print(f"T1: {len(steps) - len(fails)}/{len(steps)} ok {counts} "
          f"{time.time() - t0:.1f}s", flush=True)
    (ART / "t1-loop180.json").write_text(
        json.dumps({"fails": fails, "counts": counts,
                    "seconds": round(time.time() - t0, 1)}, indent=1),
        encoding="utf-8")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
