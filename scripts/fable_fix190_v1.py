#!/usr/bin/env python3
"""Experiment 190 -- V1 sealed case driver (Muse).

Runs the sealed artifacts/fable-reverse190-20260922/case190.json turn by
turn through a fresh loop190 agent AND, in lockstep, a fresh loop138g
agent. Checks:
  - single/multi/corrected/nomatch/unknown: loop190 reply == sealed
    expect (exact), and the ask wrote nothing (triples unchanged);
  - teach/correct/trap: loop190 reply byte-identical to loop138g AND
    stored triples identical after the turn.
Writes rows + summary into artifacts/fable-reverse190-20260922/ only.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix190_v1.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138g_agent as L138G  # noqa: E402 (base, read-only)
import fable_loop190_agent as L190  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-reverse190-20260922"
ASK_KINDS = ("single", "multi", "corrected", "nomatch", "unknown")


def triples(loop) -> list[list[str]]:
    return [list(t) for t in L90.notebook_triples(loop.nb)]


def main() -> int:
    case = json.loads((ART / "case190.json").read_text(encoding="utf-8"))
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="v1-190-") as d190, \
            tempfile.TemporaryDirectory(prefix="v1-138g-") as d138:
        cfg190 = copy.deepcopy(L190.DEFAULT_CONFIG190)
        cfg190["state_dir"] = d190
        cfg190["sleep_threshold"] = 100000
        cfg138 = copy.deepcopy(L138G.DEFAULT_CONFIG138G)
        cfg138["state_dir"] = d138
        cfg138["sleep_threshold"] = 100000
        new = L190.build_agent190(cfg190)
        base = L138G.build_agent138g(cfg138)
        rows = []
        for step in case["turns"]:
            before = triples(new)
            r_new = " ".join(new.turn(step["turn"])).strip()
            r_base = " ".join(base.turn(step["turn"])).strip()
            after = triples(new)
            after_base = triples(base)
            kind = step["kind"]
            checks: dict = {"reply190": r_new, "reply138g": r_base,
                            "wrote": after != before}
            if kind in ASK_KINDS:
                ok = (r_new == step["expect"]) and (after == before)
                checks["expect"] = step["expect"]
                checks["match_expect"] = (r_new == step["expect"])
                checks["nowrite"] = (after == before)
            else:
                ok = (r_new == r_base) and (after == after_base)
                checks["identical"] = (r_new == r_base)
                checks["stored_identical"] = (after == after_base)
            rows.append({"id": step["id"], "kind": kind,
                         "turn": step["turn"],
                         "verdict": "OK" if ok else "FAIL", **checks})
    counter = Counter((r["kind"], r["verdict"]) for r in rows)
    ask_ok = sum(1 for r in rows
                 if r["kind"] in ASK_KINDS and r["verdict"] == "OK")
    trap_ok = sum(1 for r in rows
                  if r["kind"] not in ASK_KINDS and r["verdict"] == "OK")
    summary = {"n": len(rows),
               "by_kind_verdict": {f"{k}/{v}": c
                                   for (k, v), c in sorted(counter.items())},
               "ask_ok": ask_ok,
               "ask_total": sum(1 for r in rows if r["kind"] in ASK_KINDS),
               "trap_ok": trap_ok,
               "trap_total": sum(1 for r in rows
                                 if r["kind"] not in ASK_KINDS),
               "pass": all(r["verdict"] == "OK" for r in rows),
               "seconds": round(time.time() - t0, 1)}
    (ART / "v1-rows190.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    (ART / "v1-summary190.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(f"V1: {ask_ok}/{summary['ask_total']} asks, "
          f"{trap_ok}/{summary['trap_total']} traps, "
          f"PASS={summary['pass']} in {summary['seconds']}s", flush=True)
    for r in rows:
        if r["verdict"] != "OK":
            print(f"  FAIL {r['id']} {r['turn']!r}: got {r['reply190']!r}",
                  flush=True)
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
