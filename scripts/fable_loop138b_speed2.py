#!/usr/bin/env python3
"""Exp 138b B7 backup driver -- 15k-fact ask time, loop138b vs loop138.

Backup method (see deviation D3 in RESULTS.md): the turn-built 15k teach
ran ~4 turns/s under parallel load and could not finish in the wave
budget, so the 15k-fact notebook is built through the REAL doorway
(loop.listening._teach, the same call the loop's own _act path makes for
every teach -- same FACT records, same notebook class, no ears parsing).
The notebook is copied, both agents boot on identical state, and 25
taught-entity asks are timed per arm (process_time, in-process). The
measured quantity -- ask time over 15k facts through the full turn path
(ears composers over 15k triples + reasoner + mouth, router included on
misses) -- is identical in construction to the primary method.

Outputs into artifacts/fable-agent138b-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138b_speed2.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138_agent as L138  # noqa: E402 (frozen base, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138b-20260922"

N_SAMPLE = 25
TARGET = 15000
RELS = ["city", "color", "food", "mood", "pet", "song"]


def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, int(q * len(s))))]


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    work = ART / "work-speed2"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    dir138 = work / "nb138"
    cfg = copy.deepcopy(L138.DEFAULT_CONFIG138)
    cfg["state_dir"] = str(dir138)
    cfg["sleep_threshold"] = 100000
    loop = L138.build_agent138(cfg)
    i = 0
    while sum(1 for f in loop.nb.facts.values()
              if f.get("source") == "taught") < TARGET:
        rel = RELS[i % len(RELS)]
        said = loop.listening._teach(f"SpeedP{i:05d}", rel, "=",
                                     f"SpeedV{i:05d}", False)
        if not str(said).startswith("Saved"):
            raise RuntimeError(f"doorway refused at {i}: {said!r}")
        i += 1
    print(f"B7 backup: taught {i} facts", flush=True)
    dir138b = work / "nb138b"
    shutil.copytree(dir138, dir138b)
    facts = [f for f in loop.nb.facts.values()
             if f.get("source") == "taught"]
    asks = []
    for k in range(N_SAMPLE):
        f = facts[(k * 37) % len(facts)]
        asks.append(f"What is {loop.nb.entities[f['subject']]}'s "
                    f"{f['relation']}?")
    del loop
    out: dict = {"target_facts": TARGET, "method": "doorway-built",
                 "arms": {}}
    for tag, mod, build in (("loop138", L138, L138.build_agent138),
                            ("loop138b", L138b, L138b.build_agent138b)):
        d = dir138 if tag == "loop138" else dir138b
        cfg2 = copy.deepcopy(mod.DEFAULT_CONFIG138 if tag == "loop138"
                             else mod.DEFAULT_CONFIG138B)
        cfg2["state_dir"] = str(d)
        cfg2["sleep_threshold"] = 100000
        lp = build(cfg2)
        n = sum(1 for f in lp.nb.facts.values()
                if f.get("source") == "taught")
        assert n >= TARGET, (tag, n)
        xs = []
        for tx in asks:
            u0 = time.process_time()
            lp.turn(tx)
            xs.append((time.process_time() - u0) * 1000.0)
        out["arms"][tag] = {"taught_facts": n,
                            "ask_ms_p50": round(pct(xs, 0.5), 3),
                            "ask_ms": [round(x, 2) for x in xs]}
        print(f"B7 backup {tag}: p50 ask "
              f"{out['arms'][tag]['ask_ms_p50']} ms", flush=True)
        del lp
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "speed138b.json").write_text(json.dumps(out, indent=1),
                                        encoding="utf-8")
    print(f"B7 backup done in {out['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
