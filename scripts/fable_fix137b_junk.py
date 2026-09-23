#!/usr/bin/env python3
"""Experiment 137b G3-junk driver -- junk-write suites through loop137b.

Same four suites as scripts/fable_loop138b_junk.py (judges imported
read-only; only the agent/daemon factory is loop137b), compared per-case
against loop138b's own frozen rows in
artifacts/fable-agent138b-20260922/ (redteam136-loop138b.json,
probe150-loop138b.json, f1-loop138b.json, probe139b-loop138b.json).
Bar: 0 new WRONG/WRONG-WRITE vs loop138b; every move listed; C089/C122
must store junk-free triples. Outputs into
artifacts/fable-discourse137b-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137b_junk.py
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

import fable_fix137b_discourse as D137B  # noqa: E402 (rule under test)
import fable_fix139b_probe as P139b  # noqa: E402 (judge, read-only)
import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
import fable_fix150_probe as P150  # noqa: E402 (judge, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop137b_agent as L137B  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-discourse137b-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
ART139B = ROOT / "artifacts" / "fable-fix139b-20260922"
ART144 = ROOT / "artifacts" / "fable-fix144-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"


def build137b(extra: dict) -> object:
    cfg = copy.deepcopy(L137B.DEFAULT_CONFIG137B)
    cfg.update(extra)
    return L137B.build_agent137b(cfg)


def new_daemon137b(root: Path):
    cfg = copy.deepcopy(L137B.DEFAULT_CONFIG137B)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L137B.Loop137bDaemon(root, cfg=cfg, idle_seconds=3600.0)


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                         sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def junk_in_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        for tr in (r.get("stored") or []):
            for name in (tr[0], tr[2] if len(tr) > 2 else ""):
                if D137B.is_discourse_name(name):
                    out.append({"id": r.get("id"), "name": name})
    return out


def read_sealed138b(name: str) -> list[dict]:
    txt = (ART138B / name).read_text(encoding="utf-8")
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
            moves.append({"id": r["id"], "loop138b": b.get("verdict"),
                          "loop137b": r.get("verdict"),
                          "reply138b": str(b.get("reply", ""))[:120],
                          "reply137b": str(r.get("reply", ""))[:120]})
            if r.get("verdict") in ("WRONG-WRITE", "WRONG-ANSWER", "WRONG",
                                    "WRONG-REPLY") and b.get("verdict") not in (
                    "WRONG-WRITE", "WRONG-ANSWER", "WRONG", "WRONG-REPLY"):
                new_wrong += 1
    return moves, new_wrong


def run_redteam136() -> dict:
    R136.new_daemon139b = new_daemon137b  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows(ART / "redteam136-loop137b.json", rows)
    base = read_sealed138b("redteam136-loop138b.json")
    moves, new_wrong = verdict_moves(rows, base, "redteam136")
    junk = junk_in_rows(rows)
    junk_base = junk_in_rows(base)
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_loop138b": new_wrong, "moves": moves,
            "junk137b": junk, "junk138b": junk_base}


def run_cases150() -> dict:
    cases = json.loads((ART150 / "cases150.json").read_text(
        encoding="utf-8"))
    rows = [P150.run_case(row, build137b) for row in cases]
    write_rows(ART / "probe150-loop137b.json", rows)
    base = read_sealed138b("probe150-loop138b.json")
    moves, new_wrong = verdict_moves(rows, base, "cases150")
    return {"suite": "cases150", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_loop138b": new_wrong,
            "moves_vs_loop138b": moves, "junk137b": junk_in_rows(rows)}


def run_f1() -> dict:
    cases = json.loads((ART144 / "f1-cases.json").read_text(
        encoding="utf-8"))["cases"]
    rows = []
    for row in cases:
        t0 = time.time()
        with tempfile.TemporaryDirectory(
                prefix=row["id"] + "_") as tmp:
            try:
                loop = build137b({"state_dir": tmp,
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
    write_rows(ART / "f1-loop137b.json", rows)
    base = read_sealed138b("f1-loop138b.json")
    moves, new_wrong = verdict_moves(rows, base, "f1")
    return {"suite": "f1", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_loop138b": new_wrong,
            "moves_vs_loop138b": moves, "junk137b": junk_in_rows(rows)}


def run_cases139b() -> dict:
    cases = json.loads((ART139B / "cases139b.json").read_text(
        encoding="utf-8"))
    cases139 = json.loads(
        (ROOT / "artifacts" / "fable-fix139-20260922" / "cases139.json").read_text(
            encoding="utf-8"))
    if isinstance(cases139, dict):
        cases139 = cases139.get("cases", cases139)
    cases = list(cases139) + list(cases)
    rows = [P139b.run_case(row, build137b) for row in cases]
    write_rows(ART / "probe139b-loop137b.json", rows)
    base = read_sealed138b("probe139b-loop138b.json")
    moves, new_wrong = verdict_moves(rows, base, "cases139b")
    return {"suite": "cases139b", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_loop138b": new_wrong,
            "moves_vs_loop138b": moves, "junk137b": junk_in_rows(rows)}


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    out: dict = {}
    for fn in (run_redteam136, run_cases150, run_f1, run_cases139b):
        rep = fn()
        out[rep["suite"]] = rep
        nmoves = len(rep.get("moves", []) or []) + len(
            rep.get("moves_vs_loop138b", []) or [])
        print(f"G3-junk {rep['suite']}: n={rep['n']} {rep['counter']} "
              f"moved={nmoves} new_wrong={rep.get('new_wrong_vs_loop138b')} "
              f"junk137b={len(rep.get('junk137b', []))}", flush=True)
        for key in ("moves", "moves_vs_loop138b"):
            for m in rep.get(key, []) or []:
                print(f"  {key} {m}", flush=True)
        for j in rep.get("junk137b", []) or []:
            print(f"  JUNK {j}", flush=True)
        if rep.get("new_wrong_vs_loop138b"):
            rc = 1
        if rep.get("junk137b"):
            rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "junk137b-summary.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G3-junk {out['seconds']}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
