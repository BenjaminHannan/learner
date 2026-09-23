#!/usr/bin/env python3
"""Exp 158c G3 driver -- junk + redteam143 + sessions152 through loop158c.

Reuses the sealed judges BY IMPORT (only the agent/daemon under test is
swapped to loop158c) and compares per-case against loop158b's own frozen
results in artifacts/fable-whrel158b-20260922/:
  redteam136 vs redteam136-loop158b.json (0 new WRONG-WRITE),
  cases150   vs probe150-loop158b.json (0 verdict/reply moves),
  f1         vs fable f1-loop158b.json (same verdicts),
  cases139b  vs probe139b-loop158b.json (0 verdict moves),
  redteam143 vs redteam143-loop158b.json (0 new WRONG-ANSWER),
  sessions152 vs sessions152-loop158b.json (0 new WRONG).
Every move listed (prediction: none). Outputs into
artifacts/fable-whcity158c-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix158c_redteam.py
"""

from __future__ import annotations

import copy
import json
import shutil
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
import fable_loop158c_agent as L158c  # noqa: E402 (agent under test)
import fable_redteam143_run as R143  # noqa: E402 (cases+judge, read-only)
import fable_session152_run as S152R  # noqa: E402 (sessions+judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-whcity158c-20260922"
ART158B = ROOT / "artifacts" / "fable-whrel158b-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
ART139B = ROOT / "artifacts" / "fable-fix139b-20260922"
ART144 = ROOT / "artifacts" / "fable-fix144-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"


def build158c(extra: dict) -> object:
    cfg = copy.deepcopy(L158c.DEFAULT_CONFIG158C)
    cfg.update(extra)
    return L158c.build_agent158c(cfg)


def new_daemon158c(root: Path):
    cfg = copy.deepcopy(L158c.DEFAULT_CONFIG158C)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L158c.Loop158cDaemon(root, cfg=cfg, idle_seconds=3600.0)


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                         sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8")
            .splitlines() if l.strip()]


def run_redteam136() -> dict:
    R136.new_daemon139b = new_daemon158c  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows(ART / "redteam136-loop158c.json", rows)
    base = load_jsonl(ART158B / "redteam136-loop158b.json")
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "loop158b": b["verdict"],
                          "loop158c": r["verdict"]})
            if (r["verdict"] == "WRONG-WRITE"
                    and b["verdict"] != "WRONG-WRITE"):
                new_wrong += 1
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_loop158b": new_wrong, "moves": moves}


def run_cases150() -> dict:
    cases = json.loads((ART150 / "cases150.json").read_text(
        encoding="utf-8"))
    rows = [P150.run_case(row, build158c) for row in cases]
    write_rows(ART / "probe150-loop158c.json", rows)
    base = load_jsonl(ART158B / "probe150-loop158b.json")
    b_by_id = {r["id"]: r for r in base}
    moves = []
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"] or r["reply"] != b["reply"]:
            moves.append({"id": r["id"], "loop158b": b["verdict"],
                          "loop158c": r["verdict"]})
    return {"suite": "cases150", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves": moves}


def run_f1() -> dict:
    cases = json.loads((ART144 / "f1-cases.json").read_text(
        encoding="utf-8"))["cases"]
    rows = []
    for row in cases:
        t0 = time.time()
        with tempfile.TemporaryDirectory(
                prefix=row["id"] + "_") as tmp:
            try:
                loop = build158c({"state_dir": tmp,
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
    write_rows(ART / "f1-loop158c.json", rows)
    base = load_jsonl(ART158B / "f1-loop158b.json")
    b_by_id = {r["id"]: r for r in base}
    moves = [{"id": r["id"], "loop158b": b_by_id[r["id"]]["verdict"],
              "loop158c": r["verdict"]}
             for r in rows
             if r["id"] in b_by_id
             and r["verdict"] != b_by_id[r["id"]]["verdict"]]
    return {"suite": "f1", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves": moves}


def run_cases139b() -> dict:
    cases = json.loads((ART139B / "cases139b.json").read_text(
        encoding="utf-8"))
    cases139 = json.loads(
        (ROOT / "artifacts" / "fable-fix139-20260922" / "cases139.json")
        .read_text(encoding="utf-8"))
    if isinstance(cases139, dict):
        cases139 = cases139.get("cases", cases139)
    cases = list(cases139) + list(cases)
    rows = [P139b.run_case(row, build158c) for row in cases]
    write_rows(ART / "probe139b-loop158c.json", rows)
    base = load_jsonl(ART158B / "probe139b-loop158b.json")
    b_by_id = {r["id"]: r for r in base}
    moves = [{"id": r["id"], "loop158b": b_by_id[r["id"]]["verdict"],
              "loop158c": r["verdict"]}
             for r in rows
             if r["id"] in b_by_id
             and r["verdict"] != b_by_id[r["id"]]["verdict"]]
    return {"suite": "cases139b", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves": moves}


def run_redteam143() -> dict:
    R143.Loop132Daemon = L158c.Loop158cDaemon  # type: ignore[method-assign]
    cfg = copy.deepcopy(L158c.DEFAULT_CONFIG158C)
    cfg["sleep_threshold"] = 100000
    R143.DEFAULT_CONFIG132 = cfg  # type: ignore[method-assign]
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop158c"
    rows: list[dict] = []
    for case in suite["cases"]:
        rows.append(R143.run_case(case, scratch / case["id"], markers))
    (ART / "redteam143-loop158c.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base = json.loads((ART158B / "redteam143-loop158b.json")
                      .read_text(encoding="utf-8"))["rows"]
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "loop158b": b["verdict"],
                          "loop158c": r["verdict"],
                          "reply158b": str(b.get("reply", ""))[:120],
                          "reply158c": str(r.get("reply", ""))[:120]})
            if (r["verdict"] == "WRONG-ANSWER"
                    and b["verdict"] != "WRONG-ANSWER"):
                new_wrong += 1
    return {"suite": "redteam143", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_loop158b": new_wrong, "moves": moves}


def run_sessions() -> dict:
    out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop158c" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L158c.DEFAULT_CONFIG158C)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L158c.Loop158cDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        out[s["id"]] = judged
    (ART / "sessions152-loop158c.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    base = json.loads((ART158B / "sessions152-loop158b.json")
                      .read_text(encoding="utf-8"))
    moves, new_wrong, reply_diffs = [], 0, 0
    for sid, turns in out.items():
        for t, b in zip(turns, base.get(sid, [])):
            if str(t.get("reply", "")).strip() != str(b.get("reply", "")).strip():
                reply_diffs += 1
            if t["verdict"] != b["verdict"]:
                moves.append({"session": sid, "n": t["n"],
                              "loop158b": b["verdict"],
                              "loop158c": t["verdict"]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
    return {"suite": "sessions152", "reply_diffs": reply_diffs,
            "new_wrong_vs_loop158b": new_wrong, "moves": moves}


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    out: dict = {}
    for fn in (run_redteam136, run_cases150, run_f1, run_cases139b,
               run_redteam143, run_sessions):
        rep = fn()
        out[rep["suite"]] = rep
        movekeys = [k for k in rep if k.startswith("move")]
        nmoves = sum(len(rep.get(k, []) or []) for k in movekeys)
        print(f"G3 {rep['suite']}: n={rep.get('n', '?')} "
              f"{rep.get('counter', '')} moved={nmoves} "
              f"reply_diffs={rep.get('reply_diffs', 0)}", flush=True)
        for key in ("moves",):
            for m in rep.get(key, []) or []:
                print(f"  MOVE {m}", flush=True)
        if rep.get("new_wrong_vs_loop158b"):
            rc = 1
        for m in rep.get("moves", []) or []:
            if m.get("loop158c") in ("WRONG-WRITE", "WRONG-ANSWER",
                                     "WRONG-REPLY", "WRONG"):
                rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "redteam158c-summary.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G3 {out['seconds']}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
