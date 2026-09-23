#!/usr/bin/env python3
"""Exp 193 A1 -- sealed apos case file through loop193 vs loop138h.

Reads artifacts/fable-apos193-20260922/case193.json (sealed). Runs the
dialogue on a fresh loop193 and the twin dialogue on a fresh loop138h,
checking per-turn:
  - cap      : same turn, replies byte-identical 193 vs 138h
  - ask      : 193 reply(turn) == 138h reply(twin), 0 notebook writes
               on either loop
  - teach    : 193 reply(turn) == 138h reply(twin) and the fact
               delta == twin's fact delta (silent repair: no confirm)
  - trap     : same turn on both loops, replies byte-identical AND
               fact deltas identical
Exits 0 iff every check passes. Prints one line per turn (never averaged).

Run (Mac CPU, offline; only AFTER PASSMARKS.md + case file are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix193_probe.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop138h_agent as L138H  # noqa: E402 (base, read-only)
import fable_loop193_agent as L193  # noqa: E402 (agent under test, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-apos193-20260922"


def triples(loop) -> list[list[str]]:
    return sorted([list(t) for t in L90.notebook_triples(loop.nb)])


def fresh(which: str):
    tmp = tempfile.mkdtemp(prefix=f"loop193-a1-{which}-")
    if which == "193":
        return L193.build_agent193({"state_dir": tmp,
                                    "sleep_threshold": 100000})
    return L138H.build_agent138h({"state_dir": tmp,
                                  "sleep_threshold": 100000})


def main(argv=None) -> int:
    t0 = time.time()
    case_path = ART / "case193.json"
    steps = json.loads(case_path.read_text(encoding="utf-8"))
    loop193 = fresh("193")
    loop138 = fresh("138h")
    fails: list[dict] = []
    counts = {"cap": 0, "ask": 0, "teach": 0, "trap": 0}

    def turn(loop, text: str) -> str:
        return " ".join(loop.turn(text))

    for s in steps:
        kind = s["kind"]
        if kind == "cap":
            r193, r138 = turn(loop193, s["turn"]), turn(loop138, s["turn"])
            ok = r193 == r138
            detail = f"193={r193!r} 138h={r138!r}"
        elif kind == "ask":
            before193, before138 = triples(loop193), triples(loop138)
            r193, r138 = turn(loop193, s["turn"]), turn(loop138, s["twin"])
            nowrite = (triples(loop193) == before193
                       and triples(loop138) == before138)
            ok = r193 == r138 and nowrite
            detail = (f"193={r193!r} twin={r138!r} "
                      f"nowrites={nowrite}")
        elif kind == "teach":
            before193, before138 = triples(loop193), triples(loop138)
            r193 = turn(loop193, s["turn"])
            r_twin = turn(loop138, s["twin"])
            d193 = sorted([list(t) for t in triples(loop193)
                           if list(t) not in before193])
            d138 = sorted([list(t) for t in triples(loop138)
                           if list(t) not in before138])
            events_ok = (d193 == d138
                         and sorted(triples(loop193))
                         == sorted(triples(loop138)))
            ok = r193 == r_twin and events_ok
            detail = (f"193={r193!r} twin={r_twin!r} "
                      f"d193={d193} d138={d138} events_ok={events_ok}")
        elif kind == "trap":
            before193, before138 = triples(loop193), triples(loop138)
            r193, r138 = turn(loop193, s["turn"]), turn(loop138, s["turn"])
            d193 = sorted([list(t) for t in triples(loop193)
                           if list(t) not in before193])
            d138 = sorted([list(t) for t in triples(loop138)
                           if list(t) not in before138])
            ok = r193 == r138 and d193 == d138
            detail = (f"193={r193!r} 138h={r138!r} "
                      f"d193={d193} d138={d138}")
        else:
            fails.append({"id": s.get("id"), "err": "bad-kind"})
            continue
        counts[kind] += 1
        print(f"{'OK ' if ok else 'FAIL'} {s.get('id')} [{kind}] "
              f"{s['turn']!r} :: {detail}", flush=True)
        if not ok:
            fails.append({"id": s.get("id"), "kind": kind,
                          "turn": s["turn"], "detail": detail})

    print(f"A1: {len(steps) - len(fails)}/{len(steps)} ok {counts} "
          f"{time.time() - t0:.1f}s", flush=True)
    (ART / "t1-loop193.json").write_text(
        json.dumps({"fails": fails, "counts": counts,
                    "seconds": round(time.time() - t0, 1)}, indent=1),
        encoding="utf-8")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
