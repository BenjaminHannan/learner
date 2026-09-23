#!/usr/bin/env python3
"""Exp 187 S1 -- sealed self-question case file through loop187 vs loop138g.

Reads artifacts/fable-selfq187-20260922/case187.json (sealed). Runs the
dialogue in order on a fresh loop187 and the twin dialogue on a fresh
loop138g, checking per-turn:
  - setup : replies byte-identical 187 vs 138g
  - self  : 187 reply == the matching 187 self answer (MAKER187 /
            IDENTITY187 / NAME187 exact; cando == 138g's canonical
            "What can you do?" reply), never the D8 user-name reply,
            never the generic decline
  - trap  : same turn byte-identical 187 vs 138g
  - stmt  : same turn byte-identical 187 vs 138g + notebook triples
            unchanged on both (0 writes)
Exits 0 iff every check passes. Prints one line per turn (never averaged).

Run (Mac CPU, offline; only AFTER PASSMARKS.md + case file are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix187_probe.py
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
import fable_loop138g_agent as L138G  # noqa: E402 (base, read-only)
import fable_loop187_agent as L187  # noqa: E402 (agent under test, read-only)
import fable_self105 as S105  # noqa: E402 (decline text, read-only)
import fable_loop138_agent as L138  # noqa: E402 (decline suffix, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-selfq187-20260922"

USER_NAME_REPLY = "You never told me your name, so I do not know it."
GENERIC_DECLINE = S105.HONEST_DECLINE + L138.DECLINE_SUFFIX


def triples(loop) -> list[list[str]]:
    return sorted([list(t) for t in L90.notebook_triples(loop.nb)])


def fresh(which: str):
    tmp = tempfile.mkdtemp(prefix=f"loop187-s1-{which}-")
    if which == "187":
        return L187.build_agent187({"state_dir": tmp,
                                    "sleep_threshold": 100000})
    return L138G.build_agent138g({"state_dir": tmp,
                                  "sleep_threshold": 100000})


def main(argv=None) -> int:
    t0 = time.time()
    steps = json.loads((ART / "case187.json").read_text(encoding="utf-8"))
    loop187 = fresh("187")
    loop138 = fresh("138g")

    def turn(loop, text: str) -> str:
        return " ".join(loop.turn(text))

    canon_cando = turn(loop138, "What can you do?")
    want = {"maker": L187.MAKER187, "identity": L187.IDENTITY187,
            "name": L187.NAME187, "cando": canon_cando}
    # Canonical cando must itself be the lineage answer (sanity: 138g
    # answers "What can you do?" with the C24 sheet, not a decline).
    assert "I can:" in canon_cando, canon_cando

    fails: list[dict] = []
    counts = {"setup": 0, "self": 0, "trap": 0, "stmt": 0}
    n_self = sum(1 for s in steps if s["kind"] == "self")
    n_trap = sum(1 for s in steps if s["kind"] == "trap")
    n_stmt = sum(1 for s in steps if s["kind"] == "stmt")
    assert n_self >= 12 and n_trap >= 8 and n_stmt >= 6 and len(steps) >= 30, (
        n_self, n_trap, n_stmt, len(steps))

    for s in steps:
        kind = s["kind"]
        if kind == "setup":
            r187, r138 = turn(loop187, s["turn"]), turn(loop138, s["turn"])
            ok = r187 == r138
            detail = f"187={r187!r} 138g={r138!r}"
        elif kind == "self":
            r187 = turn(loop187, s["turn"])
            turn(loop138, s["turn"])
            exp = want[s["self187"]]
            ok = (r187 == exp and r187 != USER_NAME_REPLY
                  and r187 != GENERIC_DECLINE)
            detail = (f"187={r187!r} want={exp!r} "
                      f"is_username={r187 == USER_NAME_REPLY} "
                      f"is_decline={r187 == GENERIC_DECLINE}")
        elif kind == "trap":
            r187, r138 = turn(loop187, s["turn"]), turn(loop138, s["turn"])
            ok = r187 == r138
            detail = f"187={r187!r} 138g={r138!r}"
        elif kind == "stmt":
            b187, b138 = triples(loop187), triples(loop138)
            r187, r138 = turn(loop187, s["turn"]), turn(loop138, s["turn"])
            nowrite = triples(loop187) == b187 and triples(loop138) == b138 \
                and triples(loop187) == triples(loop138)
            ok = r187 == r138 and nowrite
            detail = (f"187={r187!r} 138g={r138!r} nowrite={nowrite}")
        else:
            fails.append({"id": s.get("id"), "err": "bad-kind"})
            continue
        counts[kind] += 1 if ok else 0
        print(f"{s['id']}({kind}): {'OK' if ok else 'FAIL'} {detail}",
              flush=True)
        if not ok:
            fails.append({"id": s.get("id"), "detail": detail})
    secs = round(time.time() - t0, 1)
    total = len(steps)
    got = sum(counts.values())
    rep = {"pass": got == total and not fails, "got": got, "of": total,
           "counts": counts, "seconds": secs, "fails": fails}
    (ART / "t1-loop187.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"S1 {got}/{total} {counts} {secs}s -> "
          f"{'PASS' if rep['pass'] else 'FAIL'}", flush=True)
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
