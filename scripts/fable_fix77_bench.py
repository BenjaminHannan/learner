#!/usr/bin/env python3
"""Experiment 77 driver for mark F4: bench65 notebook-arm flow with the
notebook class swapped for GatedThoughtNotebook.

fable_bench65_notebook_arm.py is imported and used as-is (never edited):
its run_item is called with the module's C swapped -- runtime-only -- for a
delegating shim whose Notebook is GatedThoughtNotebook. The reasoner stays
the stock QualifierAwareReasoner, so this measures exactly one swap.

Run:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_fix77_bench.py

Writes artifacts/fable-fix77-20260921/bench77.json.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
import fable_bench65_notebook_arm as B  # noqa: E402 (read-only; never edited)
from fable_fix77_core import GatedThoughtNotebook  # noqa: E402

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-fix77-20260921"


class _C77:
    Notebook = GatedThoughtNotebook

    def __getattr__(self, name):
        return getattr(C, name)


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    B.C = _C77()  # runtime-only swap of the notebook class; file untouched
    items = B.load_items(Path(B.DATA_DEFAULT))
    assert len(items) == 200, len(items)
    t0 = time.time()
    with tempfile.TemporaryDirectory(dir=str(ART)) as tmp:
        scratch = Path(tmp)
        rows = [B.run_item(it, scratch) for it in items]
    secs = time.time() - t0
    table = B.score(rows)
    correct = sum(cell.get("correct", 0) + cell.get("abstain_ok", 0)
                  for cell in table.values())
    wrong = sum(cell.get("wrong", 0) for cell in table.values())
    miss = sum(cell.get("miss", 0) for cell in table.values())
    disagree = sum(cell.get("contract_disagree", 0) for cell in table.values())
    for typ, cell in table.items():
        print(f"  {typ}: {cell}", flush=True)
    print(f"items=200 correct={correct} wrong={wrong} miss={miss} "
          f"contract_disagree={disagree} seconds={secs:.1f}", flush=True)
    (ART / "bench77.json").write_text(json.dumps({
        "items": 200, "correct": correct, "wrong": wrong, "miss": miss,
        "contract_disagree": disagree, "seconds": round(secs, 1),
        "table": table,
        "swap": "C.Notebook -> GatedThoughtNotebook; "
                "QualifierAwareReasoner unchanged"}, indent=1))
    good = correct == 200 and wrong == 0
    print("BENCH77", "PASS" if good else "FAIL", flush=True)
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
