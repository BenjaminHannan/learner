#!/usr/bin/env python3
"""Experiment 149, W1: re-run sealed 143 cases vs a wordmatch variant.

Reuses the SEALED runner by import (read-only): only its ART output path is
redirected to this experiment's artifact dir and its daemon/config globals
are swapped to the variant under test (same swap pattern as exp 132 Q4 and
exp 134 M2). The sealed case file is read, never written.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_wordmatch149_run143.py --variant 149
  (... --variant qrewrite)
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
MY_ART = ROOT / "artifacts" / "fable-wordmatch149-20260922"
SEALED_ART = ROOT / "artifacts" / "fable-redteam143-20260922"

import fable_redteam143_run as R143  # noqa: E402 (sealed runner, read-only)

# Redirect the runner's ART output path to this experiment's dir.
R143.ART = MY_ART


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 149 W1 143 re-run")
    ap.add_argument("--variant", default="149", choices=["149", "qrewrite"])
    args = ap.parse_args(argv)

    if args.variant == "149":
        import fable_loop149_agent as M149  # noqa: E402 (this exp)
        R143.Loop132Daemon = M149.Loop149Daemon
        R143.DEFAULT_CONFIG132 = copy.deepcopy(M149.DEFAULT_CONFIG149)
        tag = "149"
    else:
        import fable_loop149_agent as M149  # noqa: E402 (this exp)
        R143.Loop132Daemon = M149.Qrewrite149Daemon
        R143.DEFAULT_CONFIG132 = copy.deepcopy(M149.QREWRITE149_CONFIG)
        tag = "qrewrite149"

    suite = json.loads((SEALED_ART / "fable_redteam143_cases.json").read_text(
        encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = MY_ART / f"scratch143-{tag}"
    t0 = time.time()
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = R143.run_case(case, scratch / case["id"], markers)
        rows.append(rec)
        print(f"{case['id']} [{case['family']}]: {rec['verdict']} "
              f"stage={rec['stage']} reply={rec['reply'][:90]!r}", flush=True)
    seconds = round(time.time() - t0, 1)
    (MY_ART / f"fable_wordmatch149_143_{tag}_results.json").write_text(
        json.dumps({"seconds": seconds, "variant": tag, "rows": rows},
                   indent=1, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print(f"done: {Counter(r['verdict'] for r in rows)} in {seconds} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
