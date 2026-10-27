#!/usr/bin/env python3
"""Exp 174 T2 driver -- frozen suites through loop174 vs sealed loop138f rows.

Re-runs the loop138f frozen suites with ONLY the agent swapped to loop174
(judges/cases imported read-only, never edited):
  rt136    redteam136 write-guard cases (judge fable_fix139b_redteam136)
  rt143    redteam143 question cases (judge fable_redteam143_run)
  sessions exp-152 phone sessions (judge fable_session152_run)
  bench    bench121 new + old_s2fresh + Fable-Edit 200 + bench132
           (scorer fable_bench121_run)

Comparisons are per-case against the SEALED loop138f rows in
artifacts/fable-agent138f-20260922/ (read-only). Bar (PASSMARKS.md): every
suite per-case identical to loop138f (0 moves); 0 new WRONG / WRONG-WRITE /
junk writes; bench 0 new wrong. marks123_all runs separately (CLI) with its
own compare script (scripts/fable_fix174_markscmp.py).

Outputs into artifacts/fable-chainof174-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; one suite at a
time under parallel-agent load):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix174_t2suites.py --only rt136
  (... rt143 | sessions | bench | all)
"""

from __future__ import annotations

import argparse
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

import fable_bench121_run as B  # noqa: E402 (bench scorer, read-only)
import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
import fable_loop138f_agent as L138f  # noqa: E402 (base cfg ref, read-only)
import fable_loop174_agent as L174  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)
import fable_session152_run as S152R  # noqa: E402 (sessions+judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-chainof174-20260922"
ART138F = ROOT / "artifacts" / "fable-agent138f-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"

WRONG = {"WRONG", "WRONG-WRITE", "WRONG-ANSWER", "WRONG-REPLY"}


def base_cfg174(state_dir: str) -> dict:
    cfg = copy.deepcopy(L174.DEFAULT_CONFIG174)
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    return cfg


def new_daemon174(root: Path):
    return L174.Loop174Daemon(root, cfg=base_cfg174(str(root)),
                              idle_seconds=3600.0)


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                         sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def run_rt136() -> dict:
    R136.new_daemon139b = new_daemon174  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136-174"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows(ART / "redteam136-loop174.json", rows)
    base = [json.loads(l) for l in
            (ART138F / "redteam136-loop138f.json").read_text(
                encoding="utf-8").splitlines() if l.strip()]
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if (r["verdict"] != b["verdict"]
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()
                or r.get("stored", "n/a") != b.get("stored", "n/a")):
            moves.append({"id": r["id"], "loop138f": b["verdict"],
                          "loop174": r["verdict"]})
            if r["verdict"] in WRONG and b["verdict"] not in WRONG:
                new_wrong += 1
    return {"suite": "rt136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_138f": new_wrong, "moves": moves}


def run_rt143() -> dict:
    R143.Loop132Daemon = L174.Loop174Daemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L174.DEFAULT_CONFIG174)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop174"
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = R143.run_case(case, scratch / case["id"], markers)
        rows.append(rec)
    (ART / "redteam143-loop174.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base = json.loads(
        (ART138F / "redteam143-loop138f.json").read_text(encoding="utf-8"))
    b_by_id = {r["id"]: r for r in base["rows"]}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if (r["verdict"] != b["verdict"]
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()):
            moves.append({"id": r["id"], "loop138f": b["verdict"],
                          "loop174": r["verdict"]})
            if r["verdict"] in WRONG and b["verdict"] not in WRONG:
                new_wrong += 1
    return {"suite": "rt143", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_138f": new_wrong, "moves": moves}


def run_sessions() -> dict:
    out174: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop174" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        daemon = L174.Loop174Daemon(
            root, cfg=base_cfg174(str(root)), idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        out174[s["id"]] = judged
    (ART / "sessions152-loop174.json").write_text(
        json.dumps(out174, indent=1, ensure_ascii=False), encoding="utf-8")
    out138f = json.loads(
        (ART138F / "sessions152-loop138f.json").read_text(encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, []
    for sid, turns in out174.items():
        for t, b in zip(turns, out138f.get(sid, [])):
            if (t["verdict"] != b["verdict"]
                    or str(t["reply"]).strip()
                    != str(b["reply"]).strip()):
                moves.append({"session": sid, "n": t["n"],
                              "loop138f": b["verdict"],
                              "loop174": t["verdict"],
                              "text": str(t["text"])[:100]})
                if t["verdict"] in WRONG and b["verdict"] not in WRONG:
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"]})
    return {"suite": "sessions", "new_wrong_vs_138f": new_wrong,
            "moves": moves, "new_writes": new_writes}


SPLITS = (
    ("new_121_4hop", lambda: B.DATA_NEW,
     "fable_bench121_loop138f_new_121_4hop_rows.jsonl"),
    ("old_s2fresh_4hop", lambda: B.DATA_OLD,
     "fable_bench121_loop138f_old_s2fresh_4hop_rows.jsonl"),
    ("edit200", lambda: ROOT / "data" / "open" / "bench65"
     / "fable_edit_200.jsonl",
     "fable_bench121_loop138f_edit200_rows.jsonl"),
    ("bench132_4hop", lambda: ROOT / "data" / "open" / "bench132"
     / "fable_edit132_4hop.jsonl",
     "fable_bench121_loop138f_bench132_4hop_rows.jsonl"),
)


def run_bench() -> dict:
    B.Loop121Daemon = L174.Loop174Daemon
    cfg = base_cfg174("bench-placeholder")
    workroot = ART / "scratch-bench121-loop174"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    out: dict = {"suite": "bench", "splits": {}}
    for stag, getpath, sealed_name in SPLITS:
        items = [json.loads(l) for l in Path(str(getpath())).read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (ART / f"fable_bench121_loop174_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        base = [json.loads(l) for l in
                (ART138F / sealed_name).read_text(
                    encoding="utf-8").splitlines() if l.strip()]
        s_by_id = {r["id"]: r for r in base}
        moves, new_wrong = [], 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                moves.append({"id": r["id"], "loop138f": s["verdict"],
                              "loop174": r["verdict"]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        out["splits"][stag] = {**cell, "new_wrong_vs_138f": new_wrong,
                               "moves": moves}
        print(f"bench {stag}: {cell} new_wrong={new_wrong} "
              f"moves={len(moves)}", flush=True)
    return out


FNS = {"rt136": run_rt136, "rt143": run_rt143, "sessions": run_sessions,
       "bench": run_bench}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 174 T2 frozen suites")
    ap.add_argument("--only", default="all",
                    help="comma list of rt136,rt143,sessions,bench or 'all'")
    args = ap.parse_args(argv)
    ART.mkdir(parents=True, exist_ok=True)
    want = args.only.split(",")
    fns = [(k, v) for k, v in FNS.items()
           if want == ["all"] or k in want]
    t0 = time.time()
    rc = 0
    summary: dict = {}
    for key, fn in fns:
        rep = fn()
        summary[key] = rep
        moves = rep.get("moves", [])
        nmoves = len(moves) + sum(len(v.get("moves", []))
                                  for v in rep.get("splits", {}).values())
        nw = rep.get("new_wrong_vs_138f", 0) + sum(
            v.get("new_wrong_vs_138f", 0)
            for v in rep.get("splits", {}).values())
        nwrites = len(rep.get("new_writes", []))
        print(f"T2 {key}: moves={nmoves} new_wrong={nw} "
              f"new_writes={nwrites}", flush=True)
        for m in moves:
            print(f"  MOVE {m}", flush=True)
        if nmoves or nw or nwrites:
            rc = 1
    summary["seconds"] = round(time.time() - t0, 1)
    (ART / f"t2-summary-{args.only.replace(',', '+')}.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"T2 {args.only} {summary['seconds']}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
