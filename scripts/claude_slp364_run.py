#!/usr/bin/env python3
"""slp-364 registered run: the self-check gate on the blind fault bench (marks: artifacts/claude-slp364-20260925/PASSMARKS.md).

Run from the combined tree:
  python3 -B scripts/claude_slp364_run.py --out artifacts/claude-slp364-20260925/results.json [--workers 3]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def one(args) -> dict:
    idx, root = args
    import claude_slp364_bench as B
    import claude_slp364_gate as G
    import claude_slp360_test as X
    case = B.CASES[idx]
    d = Path(root) / f"case{idx:02d}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    t0 = time.time()
    row = {"id": case["id"], "kind": case["kind"], "category": case.get("category")}
    try:
        loop = B.run_case(case, str(d))
        gate = G.install_gate364(loop)
        X.force_sleep(loop)
        info = (loop.undo361_stats or {}).get("last") or {}
        row.update({"kept": bool(gate.last.get("kept")), "twin_kept": bool(getattr(gate, "sleeper_accepted", False)),
                    "reasons": gate.last.get("reasons", [])[:8], "n_reasons": gate.last.get("n_reasons"),
                    "probe_kinds": gate.last.get("kinds"),
                    "main_changed": info.get("main_notebook_changed"),
                    "not_restorable": info.get("not_restorable")})
        row["user_probes"] = [{"q": q, "reply": " ".join(loop.turn(q))} for q in case.get("probes", [])]
    except Exception as exc:  # noqa: BLE001
        import traceback
        row["error"] = f"{type(exc).__name__}: {exc}"
        row["trace"] = traceback.format_exc()[-1500:]
    row["seconds"] = round(time.time() - t0, 1)
    return row


def score(rows: list[dict]) -> dict:
    faults = [r for r in rows if r["kind"] == "fault"]
    clean = [r for r in rows if r["kind"] == "clean"]
    caught = sum(1 for r in faults if r.get("kept") is False)
    twin_caught = sum(1 for r in faults if r.get("twin_kept") is False)
    clean_rej = sum(1 for r in clean if r.get("kept") is not True)
    rejected = [r for r in rows if r.get("kept") is False]
    cats: dict = {}
    for r in faults:
        c = cats.setdefault(r.get("category"), [0, 0])
        c[0] += int(r.get("kept") is False)
        c[1] += 1
    return {"P364.1": caught >= 18, "P364.2": clean_rej <= 1, "P364.3": caught - twin_caught >= 6,
            "P364.4": all(r.get("main_changed") is False and not r.get("not_restorable") for r in rejected),
            "faults_caught": f"{caught}/{len(faults)}", "twin_caught": f"{twin_caught}/{len(faults)}",
            "clean_rejected": f"{clean_rej}/{len(clean)}", "errors": sum(1 for r in rows if "error" in r),
            "per_category": {k: f"{v[0]}/{v[1]}" for k, v in cats.items()},
            "proved_wrong": caught < 14 or clean_rej > 2}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args(argv)
    import claude_slp364_bench as B
    root = tempfile.mkdtemp(prefix="slp364-")
    n = len(B.CASES)
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        rows = list(ex.map(one, [(i, root) for i in range(n)]))
    res = {"rows": rows, "marks": score(rows)}
    Path(args.out).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res["marks"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
