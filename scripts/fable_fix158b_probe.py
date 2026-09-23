#!/usr/bin/env python3
"""Exp 158b T1/T2 driver -- sealed whrel probe through loop158b vs loop138b.

Each case runs on a FRESH in-process loop (teaches, then one question):
  - expect=exact: reply must equal want AND the question must write 0
    events (T2). The loop138b reply is recorded (evidence of the fix).
  - expect=identical: loop158b reply must be byte-identical to the loop138b
    reply AND both questions must write 0 events.

Bar (PASSMARKS.md): 40/40 exact, 24/24 identical, 0 writes on every
question, >= 95 % of must-cases exact. Outputs into
artifacts/fable-whrel158b-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix158b_probe.py
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

import fable_loop138b_agent as L138b  # noqa: E402 (frozen base, read-only)
import fable_loop158b_agent as L158b  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-whrel158b-20260922"


def fresh(tag: str):
    tmp = tempfile.mkdtemp(prefix=f"158b_{tag}_")
    if tag == "158b":
        cfg = copy.deepcopy(L158b.DEFAULT_CONFIG158B)
        cfg["state_dir"] = tmp
        cfg["sleep_threshold"] = 100000
        return L158b.build_agent158b(cfg)
    cfg = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    return L138b.build_agent138b(cfg)


def ask_once(tag: str, teaches: list[str], question: str) -> dict:
    loop = fresh(tag)
    for t in teaches:
        loop.turn(t)
    before = len(loop.nb.events)
    t0 = time.time()
    reply = " ".join(loop.turn(question)).strip()
    dt = round(time.time() - t0, 3)
    return {"reply": reply, "wrote": len(loop.nb.events) - before,
            "seconds": dt}


def run_case(row: dict, teaches: list[str]) -> dict:
    r8 = ask_once("158b", teaches, row["question"])
    out = {"id": row["id"], "shape": row.get("shape", ""),
           "question": row["question"], "reply158b": r8["reply"],
           "wrote158b": r8["wrote"], "seconds": r8["seconds"]}
    if row["expect"] == "exact":
        rb = ask_once("138b", teaches, row["question"])
        out["reply138b"] = rb["reply"]
        out["want"] = row["want"]
        out["verdict"] = ("OK" if (r8["reply"] == row["want"]
                                   and r8["wrote"] == 0) else "FAIL")
    else:
        rb = ask_once("138b", teaches, row["question"])
        out["reply138b"] = rb["reply"]
        out["wrote138b"] = rb["wrote"]
        out["verdict"] = ("OK" if (r8["reply"] == rb["reply"]
                                   and r8["wrote"] == 0
                                   and rb["wrote"] == 0) else "FAIL")
    return out


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    suite = json.loads((ART / "cases158b.json").read_text(encoding="utf-8"))
    teaches = list(suite["teaches"])
    t0 = time.time()
    rows = [run_case(r, teaches) for r in suite["cases"]]
    (ART / "probe158b-rows.json").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in rows) + "\n", encoding="utf-8")
    must = [r for r in rows if r["id"][0] in ("A", "B", "C", "D")]
    ident = [r for r in rows if r["id"][0] in ("U", "L")]
    exact_ok = sum(1 for r in must if r["verdict"] == "OK")
    ident_ok = sum(1 for r in ident if r["verdict"] == "OK")
    writes = sum(r["wrote158b"] for r in rows)
    out = {"seconds": round(time.time() - t0, 1), "n": len(rows),
           "must_ok": f"{exact_ok}/{len(must)}",
           "identical_ok": f"{ident_ok}/{len(ident)}",
           "writes158b": writes,
           "fails": [r["id"] for r in rows if r["verdict"] != "OK"]}
    (ART / "probe158b-summary.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"T1/T2 probe: must {out['must_ok']} identical {out['identical_ok']} "
          f"writes={writes} fails={out['fails']} in {out['seconds']}s",
          flush=True)
    for r in rows:
        if r["verdict"] != "OK":
            print(f"  FAIL {r['id']} {r['question']!r}: "
                  f"158b={r['reply158b']!r} "
                  f"138b={r.get('reply138b')!r} want={r.get('want')!r}",
                  flush=True)
    rc = 0 if (exact_ok == len(must) and ident_ok == len(ident)
               and writes == 0) else 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
