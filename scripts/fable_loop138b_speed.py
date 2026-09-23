#!/usr/bin/env python3
"""Exp 138b B7 driver -- 15k-fact ask time, loop138b vs loop138.

Teaches ONE 15k-fact notebook with the frozen loop138 (soak-108 plan,
seed 93, teach turns only), copies the state dir, boots loop138b on the
copy, and times 25 taught-entity asks on each (process_time, in-process,
same estimator shape as scripts/fable_perf142_c1.py). No bar beyond
reporting both numbers (the 142 index is OUT: it needs an
IndexedLoopNotebook lower-layer swap). Outputs into
artifacts/fable-agent138b-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138b_speed.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138_agent as L138  # noqa: E402 (frozen base, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (agent under test)
import fable_soak108_run as S108  # noqa: E402 (plan builder, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138b-20260922"

N_SAMPLE = 25
TARGET = 15000


def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, int(q * len(s))))]


def ntaught(loop) -> int:
    return sum(1 for f in loop.nb.facts.values()
               if f.get("source") == "taught")


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    turns, _ = S108.build_plan(40000, 93)
    work = ART / "work-speed"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    dir138 = work / "nb138"
    cfg = copy.deepcopy(L138.DEFAULT_CONFIG138)
    cfg["state_dir"] = str(dir138)
    cfg["sleep_threshold"] = 100000
    loop = L138.build_agent138(cfg)
    ti = 0
    synth = 0
    while ntaught(loop) < TARGET:
        if ti < len(turns):
            t = turns[ti]
            ti += 1
            if t["kind"] == "ask":
                continue
            loop.turn(t["text"])
        else:
            f0 = next(f for f in loop.nb.facts.values()
                      if f.get("source") == "taught"
                      and loop.nb.active(f["fact_id"])
                      and "literal" in f["value"])
            nm = loop.nb.entities[f0["subject"]]
            loop.turn(f"Actually, {nm}'s {f0['relation']} is "
                      f"{f0['value']['literal']}x{synth}.")
            synth += 1
        if ti % 5000 == 0:
            print(f"B7 teaching: {ntaught(loop)} facts", flush=True)
    dir138b = work / "nb138b"
    shutil.copytree(dir138, dir138b)
    seen = [f for f in loop.nb.facts.values()
            if f.get("source") == "taught" and loop.nb.active(f["fact_id"])]
    asks = []
    for i in range(N_SAMPLE):
        f = seen[(i * 37) % len(seen)]
        asks.append(f"What is {loop.nb.entities[f['subject']]}'s "
                    f"{f['relation']}?")
    del loop
    out: dict = {"target_facts": TARGET, "arms": {}}
    for tag, mod, build in (("loop138", L138, L138.build_agent138),
                            ("loop138b", L138b, L138b.build_agent138b)):
        d = dir138 if tag == "loop138" else dir138b
        cfg2 = copy.deepcopy(mod.DEFAULT_CONFIG138 if tag == "loop138"
                             else mod.DEFAULT_CONFIG138B)
        cfg2["state_dir"] = str(d)
        cfg2["sleep_threshold"] = 100000
        lp = build(cfg2)
        assert ntaught(lp) >= TARGET, (tag, ntaught(lp))
        xs = []
        for tx in asks:
            u0 = time.process_time()
            lp.turn(tx)
            xs.append((time.process_time() - u0) * 1000.0)
        out["arms"][tag] = {"taught_facts": ntaught(lp),
                            "ask_ms_p50": round(pct(xs, 0.5), 3),
                            "ask_ms": [round(x, 2) for x in xs]}
        print(f"B7 {tag}: p50 ask {out['arms'][tag]['ask_ms_p50']} ms",
              flush=True)
        del lp
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "speed138b.json").write_text(json.dumps(out, indent=1),
                                        encoding="utf-8")
    print(f"B7 done in {out['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
