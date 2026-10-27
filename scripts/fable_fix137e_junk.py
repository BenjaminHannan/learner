#!/usr/bin/env python3
"""Experiment 137e G3-junk driver -- junk-write suites through loop137e.

Same four suites as scripts/fable_fix137c_junk.py (judges imported
read-only; only the agent/daemon factory is loop137e), compared per-case
against loop137c's own frozen rows in
artifacts/fable-hypo137c-20260922/ (redteam136-loop137c.json,
probe150-loop137c.json, f1-loop137c.json, probe139b-loop137c.json).
Bar: 0 new WRONG/WRONG-WRITE vs loop137c; every move listed. Predicted
moves (pre-seal REAL-AGENT scan scripts/fable_fix137e_scan.py: every
suite input executed live on loop137e + loop137c, reply+writes
compared): NONE on all four suites -- redteam136 2 hearsay fires (C101
"I heard Tom's city is Rome.", C102 "Apparently Tom is French.") reply
HEARSAY_MSG on both agents, 0 writes; cases150 6 hearsay fires
(R02/R03/R04/R05/R08/A01) reply HEARSAY_MSG on both agents, 0 writes
(the 7 checks 137d broke return to identical); f1 + cases139b 0 fires.
Outputs into artifacts/fable-frame137e-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137e_junk.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix139b_probe as P139b  # noqa: E402 (judge, read-only)
import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
import fable_fix150_probe as P150  # noqa: E402 (judge, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop137e_agent as L137E  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-frame137e-20260922"
ART137C = ROOT / "artifacts" / "fable-hypo137c-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
ART139B = ROOT / "artifacts" / "fable-fix139b-20260922"
ART144 = ROOT / "artifacts" / "fable-fix144-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"


def build137e(extra: dict) -> object:
    cfg = copy.deepcopy(L137E.DEFAULT_CONFIG137E)
    cfg.update(extra)
    return L137E.build_agent137e(cfg)


def new_daemon137e(root: Path):
    cfg = copy.deepcopy(L137E.DEFAULT_CONFIG137E)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L137E.Loop137eDaemon(root, cfg=cfg, idle_seconds=3600.0)


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                         sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def read_sealed137c(name: str) -> list[dict]:
    txt = (ART137C / name).read_text(encoding="utf-8")
    try:
        d = json.loads(txt)
        if isinstance(d, dict):
            for k in ("cases", "rows"):
                if isinstance(d.get(k), list):
                    return d[k]
        if isinstance(d, list):
            return d
    except ValueError:
        pass
    return [json.loads(l) for l in txt.splitlines() if l.strip()]


def verdict_moves(rows: list[dict], base: list[dict], tag: str) -> tuple[
        list[dict], int]:
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r.get("verdict") != b.get("verdict") or (
                tag != "redteam136" and r.get("reply") != b.get("reply")):
            moves.append({"id": r["id"], "loop137c": b.get("verdict"),
                          "loop137e": r.get("verdict"),
                          "reply137c": str(b.get("reply", ""))[:120],
                          "reply137e": str(r.get("reply", ""))[:120]})
            if r.get("verdict") in ("WRONG-WRITE", "WRONG-ANSWER", "WRONG",
                                    "WRONG-REPLY") and b.get("verdict") not in (
                    "WRONG-WRITE", "WRONG-ANSWER", "WRONG", "WRONG-REPLY"):
                new_wrong += 1
    return moves, new_wrong


def run_redteam136() -> dict:
    R136.new_daemon139b = new_daemon137e  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows(ART / "redteam136-loop137e.json", rows)
    base = read_sealed137c("redteam136-loop137c.json")
    moves, new_wrong = verdict_moves(rows, base, "redteam136")
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_loop137c": new_wrong, "moves": moves}


def run_cases150() -> dict:
    cases = json.loads((ART150 / "cases150.json").read_text(
        encoding="utf-8"))
    rows = [P150.run_case(row, build137e) for row in cases]
    write_rows(ART / "probe150-loop137e.json", rows)
    base = read_sealed137c("probe150-loop137c.json")
    moves, new_wrong = verdict_moves(rows, base, "cases150")
    return {"suite": "cases150", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_loop137c": new_wrong,
            "moves_vs_loop137c": moves}


def run_f1() -> dict:
    cases = json.loads((ART144 / "f1-cases.json").read_text(
        encoding="utf-8"))["cases"]
    rows = []
    for row in cases:
        t0 = time.time()
        with tempfile.TemporaryDirectory(
                prefix=row["id"] + "_") as tmp:
            try:
                loop = build137e({"state_dir": tmp,
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
    write_rows(ART / "f1-loop137e.json", rows)
    base = read_sealed137c("f1-loop137c.json")
    moves, new_wrong = verdict_moves(rows, base, "f1")
    return {"suite": "f1", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_loop137c": new_wrong,
            "moves_vs_loop137c": moves}


def run_cases139b() -> dict:
    cases = json.loads((ART139B / "cases139b.json").read_text(
        encoding="utf-8"))
    cases139 = json.loads(
        (ROOT / "artifacts" / "fable-fix139-20260922" / "cases139.json").read_text(
            encoding="utf-8"))
    if isinstance(cases139, dict):
        cases139 = cases139.get("cases", cases139)
    cases = list(cases139) + list(cases)
    rows = [P139b.run_case(row, build137e) for row in cases]
    write_rows(ART / "probe139b-loop137e.json", rows)
    base = read_sealed137c("probe139b-loop137c.json")
    moves, new_wrong = verdict_moves(rows, base, "cases139b")
    return {"suite": "cases139b", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_loop137c": new_wrong,
            "moves_vs_loop137c": moves}


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    out: dict = {}
    for fn in (run_redteam136, run_cases150, run_f1, run_cases139b):
        rep = fn()
        out[rep["suite"]] = rep
        nmoves = len(rep.get("moves", []) or []) + len(
            rep.get("moves_vs_loop137c", []) or [])
        print(f"G3-junk {rep['suite']}: n={rep['n']} {rep['counter']} "
              f"moved={nmoves} new_wrong={rep.get('new_wrong_vs_loop137c')}",
              flush=True)
        for key in ("moves", "moves_vs_loop137c"):
            for m in rep.get(key, []) or []:
                print(f"  {key} {m}", flush=True)
        if rep.get("new_wrong_vs_loop137c"):
            rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "junk137e-summary.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G3-junk {out['seconds']}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
