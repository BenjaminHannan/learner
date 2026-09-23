#!/usr/bin/env python3
"""Exp 158c T1/T2 driver -- sealed whcity probe through loop158c vs loop158b.

Each case runs on a FRESH in-process loop (teaches, then one turn):
  - expect=exact: reply must equal want AND the question must write 0
    events (T2). The loop158b reply is recorded (evidence of the fix).
  - expect=identical: loop158c reply must be byte-identical to the loop158b
    reply AND both arms must write the same number of events (0 for
    questions; equal counts for the teach turn).

Bar (PASSMARKS.md): 22/22 exact, 24/24 identical, 0 writes on every
question, >= 95 % of must-cases exact. Outputs into
artifacts/fable-whcity158c-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix158c_probe.py
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

import fable_loop158b_agent as L158b  # noqa: E402 (frozen base, read-only)
import fable_loop158c_agent as L158c  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-whcity158c-20260922"


def fresh(tag: str):
    tmp = tempfile.mkdtemp(prefix=f"158c_{tag}_")
    if tag == "158c":
        cfg = copy.deepcopy(L158c.DEFAULT_CONFIG158C)
        cfg["state_dir"] = tmp
        cfg["sleep_threshold"] = 100000
        return L158c.build_agent158c(cfg)
    cfg = copy.deepcopy(L158b.DEFAULT_CONFIG158B)
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    return L158b.build_agent158b(cfg)


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
    r8 = ask_once("158c", teaches, row["question"])
    out = {"id": row["id"], "shape": row.get("shape", ""),
           "question": row["question"], "reply158c": r8["reply"],
           "wrote158c": r8["wrote"], "seconds": r8["seconds"]}
    if row["expect"] == "exact":
        rb = ask_once("158b", teaches, row["question"])
        out["reply158b"] = rb["reply"]
        out["want"] = row["want"]
        out["verdict"] = ("OK" if (r8["reply"] == row["want"]
                                   and r8["wrote"] == 0) else "FAIL")
    else:
        rb = ask_once("158b", teaches, row["question"])
        out["reply158b"] = rb["reply"]
        out["wrote158b"] = rb["wrote"]
        out["verdict"] = ("OK" if (r8["reply"] == rb["reply"]
                                   and r8["wrote"] == rb["wrote"]) else "FAIL")
    return out


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    suite = json.loads((ART / "cases158c.json").read_text(encoding="utf-8"))
    teaches = list(suite["teaches"])
    t0 = time.time()
    rows = [run_case(r, teaches) for r in suite["cases"]]
    (ART / "probe158c-rows.json").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in rows) + "\n", encoding="utf-8")
    must = [r for r in rows if r["id"].startswith("S")]
    ident = [r for r in rows if not r["id"].startswith("S")]
    exact_ok = sum(1 for r in must if r["verdict"] == "OK")
    ident_ok = sum(1 for r in ident if r["verdict"] == "OK")
    qwrites = sum(r["wrote158c"] for r in rows
                  if r["id"] != "O11")
    out = {"seconds": round(time.time() - t0, 1), "n": len(rows),
           "must_ok": f"{exact_ok}/{len(must)}",
           "identical_ok": f"{ident_ok}/{len(ident)}",
           "question_writes158c": qwrites,
           "fails": [r["id"] for r in rows if r["verdict"] != "OK"]}
    (ART / "probe158c-summary.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"T1/T2 probe: must {out['must_ok']} identical {out['identical_ok']} "
          f"qwrites={qwrites} fails={out['fails']} in {out['seconds']}s",
          flush=True)
    for r in rows:
        if r["verdict"] != "OK":
            print(f"  FAIL {r['id']} {r['question']!r}: "
                  f"158c={r['reply158c']!r} "
                  f"158b={r.get('reply158b')!r} want={r.get('want')!r}",
                  flush=True)
    rc = 0 if (exact_ok == len(must) and ident_ok == len(ident)
               and qwrites == 0) else 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
