#!/usr/bin/env python3
"""Exp 138e G1 driver -- bench121 new + old fresh + Fable-Edit + bench132.

Reuses artifacts/fable-agent138b-20260922/fable_loop138b_bench121.py BY
IMPORT (split table + row loader); only the daemon under test is swapped
to Loop138eDaemon. Compares per-item verdicts against the SEALED loop138b
rows (read-only). Outputs into
artifacts/fable-officechain138e-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138e_bench.py
"""

from __future__ import annotations

import copy
import importlib.util
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
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"


def _load_138b_driver():
    spec = importlib.util.spec_from_file_location(
        "fable_loop138b_bench121",
        str(ART138B / "fable_loop138b_bench121.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    D = _load_138b_driver()
    B.Loop121Daemon = L138e.Loop138eDaemon
    cfg = copy.deepcopy(L138e.DEFAULT_CONFIG138E)
    cfg["sleep_threshold"] = 100000
    ART.mkdir(parents=True, exist_ok=True)
    tag = "loop138e"
    workroot = ART / f"scratch-bench121-{tag}"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "scorer": "v2", "agent": tag,
                     "splits": {}}
    rc = 0
    for stag, path, _sealed_name in list(D.SPLITS_3) + [D.SPLIT_132]:
        items = D.load_rows(Path(str(path)))
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (ART / f"fable_bench121_{tag}_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B.summarize(rows)
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        base_path = ART138B / f"fable_bench121_loop138b_{stag}_rows.jsonl"
        base_rows = D.load_rows(base_path)
        s_by_id = {r["id"]: r for r in base_rows}
        moves, new_wrong = [], 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                moves.append({"id": r["id"], "loop138b": s["verdict"],
                              tag: r["verdict"],
                              "reply138b": s.get("reply", "")[:160],
                              "reply138e": r.get("reply", "")[:160]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        cmp = {"base": {
            "correct": sum(1 for r in base_rows
                           if r["verdict"] == "correct"),
            "abstain": sum(1 for r in base_rows
                           if r["verdict"] == "abstain"),
            "wrong": sum(1 for r in base_rows
                         if r["verdict"] == "wrong")},
            "new_wrong_vs_loop138b": new_wrong, "moves": moves}
        if new_wrong != 0:
            rc = 1
        summary["splits"][stag] = {tag: cell, "by_type": table,
                                   "compare": cmp}
        print(f"{stag}: {tag} {cell} base={cmp['base']} "
              f"new_wrong={cmp['new_wrong_vs_loop138b']} "
              f"moves={len(cmp['moves'])}", flush=True)
        for m in cmp["moves"]:
            print(f"  MOVE {m['id']}: {m['loop138b']} -> {m[tag]}",
                  flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (ART / f"fable_bench121_summary_{tag}.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G1 {summary['seconds']}s -> "
          f"{ART / ('fable_bench121_summary_' + tag + '.json')}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
