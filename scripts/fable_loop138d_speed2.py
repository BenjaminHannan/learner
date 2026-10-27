#!/usr/bin/env python3
"""Exp 138d M6 driver -- 15k-fact ask time, loop138d vs loop138b.

Same backup method as scripts/fable_loop138b_speed2.py (see its docstring):
the 15k-fact notebook is built through the REAL doorway
(loop.listening._teach, the same call the loop's own _act path makes for
every teach -- same FACT records, no ears parsing). The notebook is built
with the loop138b doorway (Loop90Notebook, proven at this scale), copied,
and loop138d boots on the copy (IndexedLoopNotebook rebuilds its index
from the same events log + seal at boot); both agents boot on identical
state, and 25 taught-entity asks are timed per arm (process_time,
in-process). Outputs into artifacts/fable-agent138d-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138d_speed2.py
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

import fable_loop138b_agent as L138b  # noqa: E402 (comparison base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138d-20260922"

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
    dir138b = work / "nb138b"
    cfg = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
    cfg["state_dir"] = str(dir138b)
    cfg["sleep_threshold"] = 100000
    loop = L138b.build_agent138b(cfg)
    i = 0
    while sum(1 for f in loop.nb.facts.values()
              if f.get("source") == "taught") < TARGET:
        rel = RELS[i % len(RELS)]
        said = loop.listening._teach(f"SpeedP{i:05d}", rel, "=",
                                     f"SpeedV{i:05d}", False)
        if not str(said).startswith("Saved"):
            raise RuntimeError(f"doorway refused at {i}: {said!r}")
        i += 1
    print(f"M6: taught {i} facts", flush=True)
    dir138d = work / "nb138d"
    shutil.copytree(dir138b, dir138d)
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
    for tag, mod, build, key in (
            ("loop138b", L138b, L138b.build_agent138b, "DEFAULT_CONFIG138B"),
            ("loop138d", L138d, L138d.build_agent138d, "DEFAULT_CONFIG138D")):
        d = dir138b if tag == "loop138b" else dir138d
        cfg2 = copy.deepcopy(getattr(mod, key))
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
        print(f"M6 {tag}: p50 ask "
              f"{out['arms'][tag]['ask_ms_p50']} ms", flush=True)
        del lp
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "speed138d.json").write_text(json.dumps(out, indent=1),
                                        encoding="utf-8")
    print(f"M6 done in {out['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
