#!/usr/bin/env python3
"""Exp 138e T1 driver -- sealed held-out officeholder set through loop138e.

Reads artifacts/fable-officechain138e-20260922/heldout138e-sealed.json
(written before any 138e run on it; 16 rewrite-right + 16 would-be-wrong
labeled by one open frozen-base run). One fresh Loop138eDaemon per item
(same harness shape as scripts/fable_bench121_run.py run_item).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138e_heldrun.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench121_run as B  # noqa: E402 (run_item/scorer, read-only)
import fable_loop138e_agent as L138e  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-officechain138e-20260922"


def main(argv=None) -> int:
    items = json.loads((ART / "heldout138e-sealed.json").read_text(
        encoding="utf-8"))
    B.Loop121Daemon = L138e.Loop138eDaemon
    cfg = copy.deepcopy(L138e.DEFAULT_CONFIG138E)
    cfg["sleep_threshold"] = 100000
    workroot = ART / "scratch-heldout-138e"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    rows = []
    for it in items:
        taught = [{"sentence_en": t["sentence_en"]} for t in it["taught"]]
        rows.append(B.run_item(
            {"id": it["id"], "question": it["question"], "taught": taught,
             "gold": it["gold"], "gold_aliases": it.get("gold_aliases", []),
             "expected": it.get("expected", "answer"),
             "type": "heldout-138e"}, workroot / it["id"],
            copy.deepcopy(cfg)))
    (ART / "heldout138e-138e_rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in rows) + "\n", encoding="utf-8")
    right = [r for r in rows if r["id"].startswith("138e-R")]
    wshape = [r for r in rows if r["id"].startswith("138e-W")]
    rep = {
        "seconds": round(time.time() - t0, 1),
        "n": len(rows),
        "wrong": sum(1 for r in rows if r["verdict"] == "wrong"),
        "right_correct": sum(1 for r in right if r["verdict"] == "correct"),
        "right_n": len(right),
        "wshape": {v: sum(1 for r in wshape if r["verdict"] == v)
                   for v in ("correct", "abstain", "wrong")},
        "moves": [{"id": r["id"], "verdict": r["verdict"],
                   "stage": r["ears_stage"],
                   "reply": r["reply"][:160]} for r in rows],
    }
    (ART / "heldout138e-summary.json").write_text(
        json.dumps(rep, indent=1, sort_keys=True), encoding="utf-8")
    print(f"T1 {rep['seconds']}s wrong={rep['wrong']} "
          f"right_correct={rep['right_correct']}/{rep['right_n']} "
          f"wshape={rep['wshape']}", flush=True)
    for r in rows:
        print(f"  {r['id']}: {r['verdict']} stage={r['ears_stage']} "
              f"{r['reply'][:110]}", flush=True)
    return 0 if rep["wrong"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
