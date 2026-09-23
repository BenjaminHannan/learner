#!/usr/bin/env python3
"""Exp 188 F1 driver -- sealed cases188.json through fresh loop188 loops.

Per turn (fresh loop each, sleep_threshold=100000):
  - statement: loop188 reply == STATEMENT_FALLBACK188 with 0 triples AND
    loop138g reply == QUESTION_FALLBACK188 with 0 triples (base check).
  - question/handled: loop188 reply byte-identical to loop138g reply AND
    triples identical (event check: 0 new writes by construction).

Writes f1-loop188.json rows into artifacts/fable-statefall188-20260922/.
Exit 0 iff every case meets its bar; any miss prints FAIL lines.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix188_f1.py
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
import fable_loop138g_agent as L138G  # noqa: E402 (base agent, read-only)
import fable_loop188_agent as L188  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-statefall188-20260922"


def fresh(kind: str, tmp: str):
    if kind == "188":
        cfg = copy.deepcopy(L188.DEFAULT_CONFIG188)
    else:
        cfg = copy.deepcopy(L138G.DEFAULT_CONFIG138G)
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    if kind == "188":
        return L188.build_agent188(cfg)
    return L138G.build_agent138g(cfg)


def one_turn(kind: str, turn: str) -> tuple[str, list]:
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="f1-188-") as tmp:
        loop = fresh(kind, tmp)
        reply = " ".join(loop.turn(turn)).strip()
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
    return reply, stored, round(time.time() - t0, 3)


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ART / "cases188.json").read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    rows: list[dict] = []
    bad = 0
    counts = {"statement": [0, 0], "question": [0, 0], "handled": [0, 0]}
    for case in cases:
        cid, kind, turn = case["id"], case["kind"], case["turn"]
        r188, s188, dt188 = one_turn("188", turn)
        r138, s138, _ = one_turn("138g", turn)
        rec = {"id": cid, "kind": kind, "turn": turn,
               "reply188": r188, "stored188": s188,
               "reply138g": r138, "stored138g": s138,
               "seconds": dt188}
        if kind == "statement":
            ok = (r188 == L188.STATEMENT_FALLBACK188 and s188 == []
                  and r138 == L188.QUESTION_FALLBACK188 and s138 == [])
            rec["verdict"] = "OK" if ok else "FAIL"
        else:
            ok = (r188 == r138 and s188 == s138)
            rec["verdict"] = "OK" if ok else "FAIL"
        counts[kind][1] += 1
        if ok:
            counts[kind][0] += 1
        else:
            bad += 1
            print(f"FAIL {cid} [{kind}] turn={turn!r}", flush=True)
            print(f"  188 : {r188!r} stored={s188}", flush=True)
            print(f"  138g: {r138!r} stored={s138}", flush=True)
        rows.append(rec)
    (ART / "f1-loop188.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    for k, (okn, n) in counts.items():
        print(f"F1 {k}: {okn}/{n}", flush=True)
    print("F1 " + ("PASS" if bad == 0 else f"FAIL ({bad})"), flush=True)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
