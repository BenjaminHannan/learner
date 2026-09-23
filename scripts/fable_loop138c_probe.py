#!/usr/bin/env python3
"""Exp 138c B4 driver -- the director's probe through loop138c.

Four untaught turns on a FRESH loop138c build (no session): "hi",
"who are you?", "What is the capital of Chile?", "Do you know Tom?".
For each turn a TWIN fresh base build (same class, same state dir shape)
answers through L134.Loop134AgentLoop.turn -- exactly the base reply the
138c rule must serve verbatim. Bar (PASSMARKS.md): 4/4 served replies
byte-identical to the twin base reply AND to the sealed probe_cases.json
expected text, with zero mashed-decline marker substrings.

Mashed-decline markers (must be absent): the loop138 DECLINE servings,
"HONEST_DECLINE + DECLINE_SUFFIX":
  "I do not know that from what you taught me"
  "I have no record of it, so I will not guess"
  "I didn't understand that, I don't know"
(the base clarify "I didn't understand that. Could you say it another
way?" is similar but distinct -- the check is on the three strings above).

Reads case file --cases (default artifacts/fable-self138c-20260922/
probe_cases.json, sealed). Outputs into --out (default same artifact
dir). Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138c_probe.py [--out DIR]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop134_agent as L134  # noqa: E402 (base reply, read-only)
import fable_loop138c_agent as L138C  # noqa: E402 (agent under test)

MASHED_MARKERS = (
    "I do not know that from what you taught me",
    "I have no record of it, so I will not guess",
    "I didn't understand that, I don't know",
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 138c B4 probe driver")
    ap.add_argument("--out", default=str(
        ROOT / "artifacts" / "fable-self138c-20260922"))
    ap.add_argument("--cases", default=str(
        ROOT / "artifacts" / "fable-self138c-20260922" / "probe_cases.json"))
    args = ap.parse_args()
    out = Path(args.out)
    t0 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    assert len(cases) == 4, len(cases)
    scratch = out / "scratch-probe138c"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    loop = L138C.build_agent138c({"state_dir": str(scratch / "c"),
                                  "sleep_threshold": 100000})
    twin = L138C.build_agent138c({"state_dir": str(scratch / "b"),
                                  "sleep_threshold": 100000})
    per, ok = [], True
    for c in cases:
        q = c["question"]
        served = " ".join(loop.turn(q))
        base = " ".join(L134.Loop134AgentLoop.turn(twin, q))
        routed = (dict(loop.last_routed) if loop.last_routed else None)
        mashed = [m for m in MASHED_MARKERS if m in served]
        match = (served == base == c["expected_base_reply"])
        item_ok = match and not mashed
        ok = ok and item_ok
        per.append({"question": q, "served": served, "base": base,
                    "expected": c["expected_base_reply"],
                    "routed": (routed["intent"] if routed else None),
                    "served_kind": (routed["served"] if routed else None),
                    "mashed_markers": mashed, "verbatim": served == base,
                    "ok": item_ok})
        print(f"{'OK ' if item_ok else 'FAIL'} {q!r} -> {served!r} "
              f"(routed={routed['intent'] if routed else None})",
              flush=True)
    rep = {"seconds": round(time.time() - t0, 1), "n": 4,
           "ok": ok, "per": per}
    (out / "fable_probe138c_results.json").write_text(
        json.dumps(rep, indent=1), encoding="utf-8")
    shutil.rmtree(scratch, ignore_errors=True)
    print(f"B4 {rep['seconds']}s ok={ok} -> "
          f"{out / 'fable_probe138c_results.json'}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
