#!/usr/bin/env python3
"""Exp 144 F2 -- benchmarks via fable_loop129b_bench by import, loop144 arm.

Same 3 splits + scorer path as scripts/fable_loop129b_bench.py (run_item,
summarize, totals imported, never copied); only the daemon class/config are
swapped to loop144. Plus the single bench132 case bench132-4hop-022 item
(same run_item shape; data/open/bench132/fable_edit132_4hop.jsonl).
Outputs (rows + summary + per-item diff vs the sealed loop129b rows) go
into artifacts/fable-fix144-20260922/ only; sealed artifacts never written.

Per-item identity vs loop129b is diffed in this script from the sealed row
files; the only predicted diffs are bench121-4hop-069 (F2 splits) and
bench132-4hop-022 (single item) -- see PASSMARKS.md.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix144_bench.py --run
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop129b_bench as B129b  # noqa: E402 (runners, read-only)
import fable_loop144_agent as L144  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-fix144-20260922"
ART129 = ROOT / "artifacts" / "fable-fix129-20260922"
DATA_132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"

SEALED_ROWS = {
    "edit200": ART129 / "fable_bench129b_loop129b_edit200_rows.jsonl",
    "old_s2fresh_4hop": ART129 / "fable_bench129b_loop129b_old_s2fresh_4hop_rows.jsonl",
    "new_121_4hop": ART129 / "fable_bench129b_loop129b_new_121_4hop_rows.jsonl",
}


def diff_rows(sealed: list[dict], mine: list[dict]) -> dict:
    by_id = {r["id"]: r for r in sealed}
    diffs = []
    for r in mine:
        s = by_id.get(r["id"])
        if s is None:
            diffs.append({"id": r["id"], "what": "missing-in-sealed"})
            continue
        for k in ("verdict", "exact", "contains_gold", "n_teach_reject",
                  "teach_replies", "extracted"):
            if r.get(k) != s.get(k):
                diffs.append({"id": r["id"], "what": k,
                              "sealed": s.get(k), "mine": r.get(k)})
    return {"n_sealed": len(sealed), "n_mine": len(mine), "diffs": diffs}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 144 bench (loop144 arm)")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args(argv)
    if not args.run:
        ap.print_help()
        return 0
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / "scratch-bench-loop144"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    cfg = copy.deepcopy(L144.DEFAULT_CONFIG144)
    cfg["sleep_threshold"] = 100000
    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2", "agent": "loop144",
                 "arms": {}, "diffs": {}}
    for tag, path in (("edit200", B129b.DATA_EDIT200),
                      ("old_s2fresh_4hop", B129b.DATA_OLD),
                      ("new_121_4hop", B129b.DATA_NEW)):
        items = [json.loads(l) for l in path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B129b.run_item(it, workroot / tag, L144.Loop144Daemon, cfg)
                for it in items]
        (ART / f"fable_bench144_loop144_{tag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B129b.summarize(rows)
        out["arms"].setdefault("loop144", {})[tag] = {
            "n": len(rows), "table": table, "totals": B129b.totals(table)}
        sealed = [json.loads(l) for l in SEALED_ROWS[tag].read_text(
            encoding="utf-8").splitlines() if l.strip()]
        out["diffs"][tag] = diff_rows(sealed, rows)
        print(f"loop144 {tag}: {B129b.totals(table)} "
              f"diffs={len(out['diffs'][tag]['diffs'])}", flush=True)
    items132 = [json.loads(l) for l in DATA_132.read_text(
        encoding="utf-8").splitlines() if l.strip()]
    item022 = next(r for r in items132 if r.get("id") == "bench132-4hop-022")
    row022 = B129b.run_item(item022, workroot / "bench132-022",
                            L144.Loop144Daemon, cfg)
    (ART / "fable_bench144_loop144_bench132-022_row.json").write_text(
        json.dumps(row022, indent=1, ensure_ascii=False), encoding="utf-8")
    out["bench132-022"] = row022
    print(f"022: verdict={row022['verdict']} exact={row022['exact']} "
          f"rejects={row022['n_teach_reject']} reply={row022['reply'][:100]}",
          flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "fable_bench144_loop144_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
