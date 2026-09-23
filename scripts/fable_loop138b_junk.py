#!/usr/bin/env python3
"""Exp 138b B3 driver -- junk-write suites re-run through the 138b agent.

Four suites, each judged by its own sealed judge (imported read-only),
each case through a FRESH in-process loop138b (same harness shape as the
probe runners: build_agent with state_dir + sleep_threshold=100000,
loop.turn, triples via notebook_triples):

  redteam136: 145 sealed cases (artifacts/fable-redteam136-20260922/
    cases136.json), judge = scripts/fable_fix139b_redteam136.run_case139b
    with only the daemon factory swapped to Loop138bDaemon; compared
    per-case against redteam136-loop139b.json (139b) and
    redteam136-loop150.json (150).
  cases150: 57 cases, judge = scripts/fable_fix150_probe.run_case;
    compared against probe150-loop150.json (must be 0 moves).
  f1: 46 cases (26 must-write + 20 two-fact), judge ported from
    scripts/fable_fix144_f1 (same verdict rules, in-process loop);
    compared against the sealed F1 expectation (26/26 + t14-only write).
  cases139b: 101 cases (56 old + 45 new), judge =
    scripts/fable_fix139b_probe.run_case; compared against
    probe139b-loop139b.json + probe139b-new-loop139b.json.

Bar (PASSMARKS.md): each suite at least as good as its own RESULTS on its
own base, 0 new wrong writes anywhere. Outputs into
artifacts/fable-agent138b-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138b_junk.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix139b_probe as P139b  # noqa: E402 (judge, read-only)
import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
import fable_fix150_probe as P150  # noqa: E402 (judge, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138b-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
ART139B = ROOT / "artifacts" / "fable-fix139b-20260922"
ART144 = ROOT / "artifacts" / "fable-fix144-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"


def build138b(extra: dict) -> object:
    cfg = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
    cfg.update(extra)
    return L138b.build_agent138b(cfg)


def new_daemon138b(root: Path):
    cfg = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L138b.Loop138bDaemon(root, cfg=cfg, idle_seconds=3600.0)


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                         sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def run_redteam136() -> dict:
    R136.new_daemon139b = new_daemon138b  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows(ART / "redteam136-loop138b.json", rows)
    base = json.loads((ART139B / "redteam136-loop139b.json").read_text(
        encoding="utf-8"))["cases"]
    base150 = json.loads((ART150 / "redteam136-loop150.json").read_text(
        encoding="utf-8"))
    if isinstance(base150, dict):
        base150 = base150.get("cases", base150)
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "loop139b": b["verdict"],
                          "loop138b": r["verdict"],
                          "reply139b": str(b.get("reply", ""))[:120],
                          "reply138b": str(r.get("reply", ""))[:120]})
            if r["verdict"] == "WRONG-WRITE" and b["verdict"] != "WRONG-WRITE":
                new_wrong += 1
    from collections import Counter
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_139b": new_wrong, "moves": moves}


def run_cases150() -> dict:
    cases = json.loads((ART150 / "cases150.json").read_text(
        encoding="utf-8"))
    rows = [P150.run_case(row, build138b) for row in cases]
    write_rows(ART / "probe150-loop138b.json", rows)
    base150d = json.loads((ART150 / "probe150-loop150.json").read_text(
        encoding="utf-8"))
    base = base150d["cases"] if isinstance(base150d, dict) else [
        json.loads(l) for l in base150d.splitlines() if l.strip()]
    b_by_id = {r["id"]: r for r in base}
    moves = []
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"] or r["reply"] != b["reply"]:
            moves.append({"id": r["id"], "loop150": b["verdict"],
                          "loop138b": r["verdict"]})
    from collections import Counter
    return {"suite": "cases150", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_loop150": moves}


def run_f1() -> dict:
    cases = json.loads((ART144 / "f1-cases.json").read_text(
        encoding="utf-8"))["cases"]
    rows = []
    for row in cases:
        t0 = time.time()
        with tempfile.TemporaryDirectory(
                prefix=row["id"] + "_") as tmp:
            try:
                loop = build138b({"state_dir": tmp,
                                  "sleep_threshold": 100000})
                reply = " ".join(loop.turn(row["text"]))
                stored = [list(t) for t in L90.notebook_triples(loop.nb)]
            except Exception as exc:  # noqa: BLE001
                rows.append({"id": row["id"], "kind": row["kind"],
                             "verdict": "HARNESS-ERROR",
                             "reply": repr(exc)[:120], "stored": []})
                continue
        rep = {"id": row["id"], "kind": row["kind"], "text": row["text"],
               "stored": stored, "reply": reply.strip()[:160],
               "seconds": round(time.time() - t0, 3)}
        if row["kind"] == "must-write":
            want = [list(row["expect"])]
            rep["expect"] = row["expect"]
            if stored == want and reply.strip().startswith("Saved:"):
                rep["verdict"] = "OK"
            elif not stored:
                rep["verdict"] = "MISSED"
            else:
                rep["verdict"] = "WRONG-WRITE"
        else:
            if not stored and not reply.strip().startswith("Saved:"):
                rep["verdict"] = "OK"
            else:
                rep["verdict"] = "WRONG-WRITE"
        rows.append(rep)
    write_rows(ART / "f1-loop138b.json", rows)
    from collections import Counter
    return {"suite": "f1", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "non_ok": [r for r in rows if r["verdict"] != "OK"]}


def run_cases139b() -> dict:
    cases = json.loads((ART139B / "cases139b.json").read_text(
        encoding="utf-8"))
    cases139 = json.loads(
        (ROOT / "artifacts" / "fable-fix139-20260922" / "cases139.json").read_text(
            encoding="utf-8"))
    if isinstance(cases139, dict):
        cases139 = cases139.get("cases", cases139)
    cases = list(cases139) + list(cases)
    rows = [P139b.run_case(row, build138b) for row in cases]
    write_rows(ART / "probe139b-loop138b.json", rows)
    base_rows = []
    for name in ("probe139b-loop139b.json", "probe139b-new-loop139b.json"):
        p = ART139B / name
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            base_rows += d["cases"] if isinstance(d, dict) else [
                json.loads(l) for l in d.splitlines() if l.strip()]
    b_by_id = {r["id"]: r for r in base_rows}
    moves = []
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "loop139b": b["verdict"],
                          "loop138b": r["verdict"]})
    from collections import Counter
    return {"suite": "cases139b", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_loop139b": moves}


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    out: dict = {}
    for fn in (run_redteam136, run_cases150, run_f1, run_cases139b):
        rep = fn()
        out[rep["suite"]] = rep
        movekeys = [k for k in rep if k.startswith("move") or k == "non_ok"]
        nmoves = sum(len(rep.get(k, []) or []) for k in movekeys)
        print(f"B3 {rep['suite']}: n={rep['n']} {rep['counter']} "
              f"moved={nmoves}", flush=True)
        for key in ("moves", "moves_vs_loop150", "moves_vs_loop139b",
                    "non_ok"):
            for m in rep.get(key, []) or []:
                print(f"  {key} {m}", flush=True)
        if rep.get("new_wrong_vs_139b"):
            rc = 1
        for key in ("moves", "moves_vs_loop150", "moves_vs_loop139b"):
            for m in rep.get(key, []) or []:
                got = m.get("loop138b", "")
                if got in ("WRONG-WRITE", "WRONG-ANSWER", "WRONG-REPLY",
                           "WRONG"):
                    rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "junk138b-summary.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"B3 {out['seconds']}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
