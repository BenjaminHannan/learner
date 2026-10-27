#!/usr/bin/env python3
"""Exp 168 G1 driver -- bench121 4 splits through loop168 vs sealed rows.

Reuses artifacts/fable-agent138b-20260922/fable_loop138b_bench121.py BY
IMPORT (load_rows + split table + data paths) and scripts/fable_bench121_run
BY IMPORT (run_item scorer v2); only the daemon class under test is swapped
to Loop168Daemon (the same swap pattern as the 138b driver). Compares
per-item verdict AND reply against the sealed loop138b rows
(fable_bench121_loop138b_*_rows.jsonl on all four splits). Bar: 0 moves, 0 new wrong. Outputs into
artifacts/fable-selfground168-20260922/bench168/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix168_bench.py
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench121_run as B  # noqa: E402 (run_item/scorer, read-only)
import fable_loop168_agent as L168  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-selfground168-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"
BENCH138B = ART138B / "fable_loop138b_bench121.py"


def load_bench138b():
    spec = importlib.util.spec_from_file_location(
        "fable_loop138b_bench121_sealed", BENCH138B)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


SEALED = {
    "new_121_4hop": "fable_bench121_loop138b_new_121_4hop_rows.jsonl",
    "old_s2fresh_4hop": "fable_bench121_loop138b_old_s2fresh_4hop_rows.jsonl",
    "edit200": "fable_bench121_loop138b_edit200_rows.jsonl",
    "bench132_4hop": "fable_bench121_loop138b_bench132_4hop_rows.jsonl",
}


def main(argv=None) -> int:
    t0 = time.time()
    bench = load_bench138b()  # reuse: split table + loaders, read-only
    B.Loop121Daemon = L168.Loop168Daemon  # type: ignore[method-assign]
    cfg = copy.deepcopy(L168.DEFAULT_CONFIG168)
    cfg["sleep_threshold"] = 100000
    work = ART / "bench168"
    if work.exists():
        import shutil
        shutil.rmtree(work)
    (work / "scratch").mkdir(parents=True)
    splits = list(bench.SPLITS_3) + [bench.SPLIT_132]
    summary: dict = {"agent": "loop168", "splits": {}}
    rc = 0
    for stag, path, _sealed in splits:
        items = bench.load_rows(Path(str(path)))
        rows = [B.run_item(it, work / "scratch" / stag, copy.deepcopy(cfg))
                for it in items]
        (work / f"fable_bench121_loop168_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        base = bench.load_rows(ART138B / SEALED[stag])
        s_by_id = {r["id"]: r for r in base}
        moves, new_wrong = [], 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"] or r.get("reply", "") != s.get(
                    "reply", ""):
                moves.append({"id": r["id"], "loop138b": s["verdict"],
                              "loop168": r["verdict"],
                              "reply138b": str(s.get("reply", ""))[:160],
                              "reply168": str(r.get("reply", ""))[:160]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        summary["splits"][stag] = {**cell, "moves": moves,
                                   "new_wrong": new_wrong}
        print(f"{stag}: loop168 {cell} moves={len(moves)} "
              f"new_wrong={new_wrong}", flush=True)
        for m in moves:
            print(f"  MOVE {m['id']}: {m['loop138b']} -> {m['loop168']}",
                  flush=True)
        if moves or new_wrong:
            rc = 1
    summary["seconds"] = round(time.time() - t0, 1)
    (work / "bench168-summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G1 {summary['seconds']}s -> {'PASS' if rc == 0 else 'FAIL'}",
          flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
