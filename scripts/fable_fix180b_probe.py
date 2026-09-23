#!/usr/bin/env python3
"""Exp 180b T1 -- sealed lowercase case file through loop180b vs loop138h.

Reads artifacts/fable-case180b-20260922/case180b.json (sealed). Runs the
dialogue on a fresh loop180b and the twin dialogue on a fresh loop138h,
checking per-turn (every seed/case reported, never averaged):
  - cap   : same turn on both loops, replies byte-identical, triple sets
            byte-identical (setup parity).
  - ask   : loop180b lowercase/mixed turn reply == loop138h twin reply,
            and loop180b writes nothing on asks.
  - teach : loop180b lowercase turn saves SILENTLY at once: reply ==
            loop138h twin reply and the full triple set == twin loop's
            triple set (same events), with no second entity differing
            from an existing one only in case.
  - trap  : same turn on both loops, replies byte-identical AND triple
            sets byte-identical (unknown names / common words / say
            pretend untouched); traps carrying "expect" (already-stored
            lowercase -> "I already have that.") must serve exactly that
            with 0 writes (the base reply is recorded, not required).
Exits 0 iff every check passes. Prints one line per turn (never averaged).

Run (Mac CPU, offline; only AFTER PASSMARKS.md + case file are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix180b_probe.py
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
import fable_loop138h_agent as L138H  # noqa: E402 (base, read-only)
import fable_loop180b_agent as L180B  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-case180b-20260922"


def triples(loop) -> list[list[str]]:
    return sorted([list(t) for t in L90.notebook_triples(loop.nb)])


def entities(loop) -> list[str]:
    try:
        return sorted([str(v) for v in loop.nb.entities.values()])
    except Exception:
        return []


def case_dupes(loop) -> list[str]:
    seen: dict[str, str] = {}
    dupes: list[str] = []
    for disp in entities(loop):
        key = disp.lower()
        if key in seen and seen[key] != disp:
            dupes.append(f"{seen[key]!r} vs {disp!r}")
        else:
            seen[key] = disp
    return dupes


def fresh(which: str):
    tmp = tempfile.mkdtemp(prefix=f"loop180b-t1-{which}-")
    if which == "180b":
        return L180B.build_agent180b({"state_dir": tmp,
                                      "sleep_threshold": 100000})
    return L138H.build_agent138h({"state_dir": tmp,
                                  "sleep_threshold": 100000})


def main(argv=None) -> int:
    t0 = time.time()
    case_path = ART / "case180b.json"
    steps = json.loads(case_path.read_text(encoding="utf-8"))
    loop180 = fresh("180b")
    loop138 = fresh("138h")
    fails: list[dict] = []
    counts = {"cap": 0, "ask": 0, "teach": 0, "trap": 0}

    def turn(loop, text: str) -> str:
        return " ".join(loop.turn(text))

    for s in steps:
        kind = s["kind"]
        if kind == "cap":
            r180, r138 = turn(loop180, s["turn"]), turn(loop138, s["turn"])
            ok = (r180 == r138
                  and triples(loop180) == triples(loop138))
            detail = f"180b={r180!r} 138h={r138!r}"
        elif kind == "ask":
            before = triples(loop180)
            r180 = turn(loop180, s["turn"])
            r138 = turn(loop138, s["twin"])
            nowrites = triples(loop180) == before
            ok = (r180 == r138 and nowrites)
            detail = (f"180b={r180!r} twin={r138!r} "
                      f"nowrites={nowrites}")
        elif kind == "teach":
            r180 = turn(loop180, s["turn"])
            r_twin = turn(loop138, s["twin"])
            events_ok = (triples(loop180) == triples(loop138))
            dupes = case_dupes(loop180)
            ok = (r180 == r_twin and events_ok and not dupes)
            detail = (f"180b={r180!r} twin={r_twin!r} "
                      f"events_ok={events_ok} dupes={dupes}")
        elif kind == "trap":
            r180, r138 = turn(loop180, s["turn"]), turn(loop138, s["turn"])
            events_ok = (triples(loop180) == triples(loop138))
            dupes = case_dupes(loop180)
            if "expect" in s:
                # Brief-mandated trap reply (already-stored lowercase ->
                # "I already have that."): 180b must serve it with 0
                # writes; the base reply is recorded, not required.
                ok = (r180 == s["expect"] and events_ok and not dupes)
                detail = (f"180b={r180!r} expect={s['expect']!r} "
                          f"138h={r138!r} events_ok={events_ok} "
                          f"dupes={dupes}")
            else:
                ok = (r180 == r138 and events_ok and not dupes)
                detail = (f"180b={r180!r} 138h={r138!r} "
                          f"events_ok={events_ok} dupes={dupes}")
        else:
            fails.append({"id": s.get("id"), "err": "bad-kind"})
            continue
        counts[kind] += 1
        print(f"{'OK ' if ok else 'FAIL'} {s.get('id')} [{kind}] "
              f"{s['turn']!r} :: {detail}", flush=True)
        if not ok:
            fails.append({"id": s.get("id"), "kind": kind,
                          "turn": s["turn"], "detail": detail})

    print(f"T1: {len(steps) - len(fails)}/{len(steps)} ok {counts} "
          f"{time.time() - t0:.1f}s", flush=True)
    (ART / "t1-loop180b.json").write_text(
        json.dumps({"fails": fails, "counts": counts,
                    "seconds": round(time.time() - t0, 1)}, indent=1),
        encoding="utf-8")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
