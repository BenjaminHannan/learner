#!/usr/bin/env python3
"""Experiment 151, Q2: re-run sealed 143 cases vs the loop132+149+qmark arm.

Reuses the SEALED runner by import (read-only): only its ART output path is
redirected to this experiment's artifact dir and its daemon/config globals
are swapped to the variant under test (same swap pattern as exps 132/149).
The sealed case file is read, never written. Variant B only (the
loop132+149 config shape); the sealed comparison rows are
artifacts/fable-wordmatch149-20260922/fable_wordmatch149_143_qrewrite149_results.json.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_qmark151_run143.py
"""

from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
MY_ART = ROOT / "artifacts" / "fable-qmark151-20260922"
SEALED_ART = ROOT / "artifacts" / "fable-redteam143-20260922"

import fable_redteam143_run as R143  # noqa: E402 (sealed runner, read-only)

# Redirect the runner's ART output path to this experiment's dir.
R143.ART = MY_ART


def main(argv=None) -> int:
    import fable_loop151_agent as M151  # noqa: E402 (this exp)
    R143.Loop132Daemon = M151.Qmark151Daemon
    R143.DEFAULT_CONFIG132 = copy.deepcopy(M151.QMARK151_CONFIG)
    tag = "qrewrite151"

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
    (MY_ART / f"fable_qmark151_143_{tag}_results.json").write_text(
        json.dumps({"seconds": seconds, "variant": tag, "rows": rows},
                   indent=1, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print(f"done: {Counter(r['verdict'] for r in rows)} in {seconds} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
