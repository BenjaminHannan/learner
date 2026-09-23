#!/usr/bin/env python3
"""Experiment 159 -- PRE-SEAL base calibration only (dev, NOT registered).

Runs the frozen cases159.json dialogues through the BASE loop150
(build_agent150, read-only) to prove every dialogue is well-formed: each
teach must reply "Saved" and each question must come back BROKEN_CHAIN
("not someone I can look up") on the base -- i.e. the base is blind to all
48, and any post-seal loop159 answer move is attributable to the one
change. Never imports fable_fix159_hop / build_agent159.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop150_agent as L150  # noqa: E402 (base, read-only)

ROOT = SCRIPTS.parent
ART159 = ROOT / "artifacts" / "fable-hop159-20260922"
BROKEN_MARK = "not someone I can look up"


def main() -> int:
    cfg = copy.deepcopy(L150.DEFAULT_CONFIG150)
    cases = json.loads((ART159 / "cases159.json").read_text(encoding="utf-8"))
    bad = 0
    for row in cases:
        with tempfile.TemporaryDirectory(prefix="cal159_") as tmp:
            loop = L150.build_agent150(dict(cfg, state_dir=tmp,
                                            sleep_threshold=100000))
            teaches = [" ".join(loop.turn(s)) for s in row["teaches"]]
            saved = all("Saved" in r for r in teaches)
            reply = " ".join(loop.turn(row["question"]))
            broken = BROKEN_MARK in reply
            ok = saved and broken
            bad += not ok
            if not ok:
                print(f"CALIB-ISSUE {row['id']}: saved={saved} "
                      f"broken={broken}", flush=True)
                for s, r in zip(row["teaches"], teaches):
                    print(f"    teach {s!r} -> {r[:100]}", flush=True)
                print(f"    q {row['question']!r} -> {reply[:130]}",
                      flush=True)
    print(f"CALIB base-loop150: {len(cases) - bad}/{len(cases)} "
          f"well-formed (teaches Saved + question BROKEN_CHAIN)")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
