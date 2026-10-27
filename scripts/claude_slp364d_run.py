#!/usr/bin/env python3
"""slp-364d registered run: gate v4 vs gate v1 on the fourth blind bench (marks: artifacts/claude-slp364d-20260925/PASSMARKS.md).

Both arms have slp-360 (scrap layer) and slp-368 (write lock); the only difference is the gate.
  V1 = claude_slp364_gate.install_gate364        V2 = claude_slp364d_gate.install_gate364d (v4 = v3 + lure rules L2 and U; label V2 kept for the scoring code)
Both arms: slp-360 + slp-368 lock + slp-369 restore + slp-361 undo.
Bench: scripts/claude_slp364d_bench.py (40 cases, written by a separate agent that was told not to open any gate).
  python3 -B scripts/claude_slp364d_run.py --out artifacts/claude-slp364d-20260925/results.json [--workers 2]
"""
from __future__ import annotations

import argparse
import hashlib
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


def _sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def one(args) -> dict:
    idx, root, arm = args
    import claude_slp364d_bench as B
    import claude_slp364_gate as G1
    import claude_slp364d_gate as G2
    import claude_slp360_test as X
    import claude_slp368_lock as L
    import claude_slp369_restore as R
    case = B.CASES[idx]
    d = Path(root) / f"{arm}-case{idx:02d}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    t0 = time.time()
    row = {"id": case["id"], "kind": case["kind"], "category": case.get("category"), "arm": arm}
    try:
        loop = B.run_case(case, str(d / "state"))
        L.install_lock368(loop)
        rs = R.install_restore369(loop)
        if arm == "V2":
            gate = G2.install_gate364d(loop, rebuild=lambda sd, s=case["seed"]: X.build(sd, s, "P"))
        else:
            gate = G1.install_gate364(loop)
        log = Path(loop.dir) / "notebook" / "events.jsonl"
        before = _sha(log)
        X.force_sleep(loop)
        after = _sha(log)
        last = gate.last
        row.update({"kept": bool(last.get("kept")), "twin_kept": bool(getattr(gate, "sleeper_accepted", False)),
                    "reasons": last.get("reasons", [])[:8], "n_reasons": last.get("n_reasons"),
                    "main_same": before == after, "p_restored": last.get("p_restored"),
                    "claimed": last.get("claimed"), "restart": last.get("restart"),
                    "restored369": rs["restored"], "kinds": last.get("kinds")})
        row["user_probes"] = [{"q": q, "reply": " ".join(loop.turn(q))} for q in case.get("probes", [])]
    except Exception as exc:  # noqa: BLE001
        import traceback
        row["error"] = f"{type(exc).__name__}: {exc}"
        row["trace"] = traceback.format_exc()[-1500:]
    row["seconds"] = round(time.time() - t0, 1)
    return row


def score(rows: list[dict]) -> dict:
    v = {a: {r["id"]: r for r in rows if r["arm"] == a} for a in ("V1", "V2")}
    faults = [i for i, r in v["V2"].items() if r["kind"] == "fault"]
    clean = [i for i, r in v["V2"].items() if r["kind"] == "clean"]
    c2 = sum(1 for i in faults if v["V2"][i].get("kept") is False)
    c1 = sum(1 for i in faults if v["V1"][i].get("kept") is False)
    twin = sum(1 for i in faults if v["V2"][i].get("twin_kept") is False)
    rej = sum(1 for i in clean if v["V2"][i].get("kept") is not True)
    main_ok = sum(1 for r in v["V2"].values() if r.get("main_same") is True and r.get("p_restored") is not False)
    same = sum(1 for i in clean if "error" not in v["V2"][i]
               and v["V2"][i].get("user_probes") == v["V1"][i].get("user_probes"))
    cats: dict = {}
    for i in faults:
        c = cats.setdefault(v["V2"][i]["category"], [0, 0, 0])
        c[0] += int(v["V2"][i].get("kept") is False)
        c[1] += int(v["V1"][i].get("kept") is False)
        c[2] += 1
    return {"P364d.1": c2 >= 18, "P364d.2": rej <= 1, "P364d.3": c2 >= c1 + 3,
            "P364d.4": main_ok == len(v["V2"]) == 40, "P364d.5": same == 20,
            "v2_caught": f"{c2}/{len(faults)}", "v1_caught": f"{c1}/{len(faults)}",
            "sleeper_flag_caught": f"{twin}/{len(faults)}", "v2_clean_rejected": f"{rej}/{len(clean)}",
            "v1_clean_rejected": f"{sum(1 for i in clean if v['V1'][i].get('kept') is not True)}/{len(clean)}",
            "main_and_sandbox_ok": f"{main_ok}/{len(v['V2'])}", "clean_replies_same": f"{same}/{len(clean)}",
            "per_category_v2_v1_n": {k: f"{a}/{c} (v1 {b})" for k, (a, b, c) in cats.items()},
            "errors": sum(1 for r in rows if "error" in r),
            "proved_wrong": c2 < 15 or rej > 2}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args(argv)
    import claude_slp364d_bench as B
    root = tempfile.mkdtemp(prefix="slp364d-")
    jobs = [(i, root, arm) for i in range(len(B.CASES)) for arm in ("V2", "V1")]
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        rows = list(ex.map(one, jobs))
    res = {"rows": rows, "marks": score(rows)}
    Path(args.out).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res["marks"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
