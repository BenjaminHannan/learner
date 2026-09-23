#!/usr/bin/env python3
"""Exp 156c S3 suites driver -- redteam136 + redteam143 + sessions152 + bench.

Mirrors scripts/fable_fix138h_suites.py (same sealed cases + judges,
read-only); only the loop under test is loop156c (fresh in-process loops
/ Loop156cDaemon with idle_seconds, sleep_threshold=100000). Compares
per-case against the SEALED loop138h rows: ZERO moves predicted
(pre-seal pure-function scan: the 156c classifier fires on none of the
suite/bench inputs; every 156c phrase is an anchored whole-message
match and every suite turn carries a name, relation, question word, or
extra token -- see PASSMARKS.md). Any move fails S3 honestly. 0 new
WRONG / WRONG-WRITE / junk writes vs loop138h throughout.

Outputs into artifacts/fable-smalltalk156c-20260922/ (my folder only).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; one suite at
a time under parallel-agent load):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix156c_suites.py --only junk|rt143|sessions|bench|all
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

import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop156c_agent as L156c  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-smalltalk156c-20260922"
ART138H = ROOT / "artifacts" / "fable-agent138h-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"


def read_rows(path: Path):
    """Read a sealed rows file (JSON array or JSONL)."""
    text = path.read_text(encoding="utf-8")
    try:
        val = json.loads(text)
        if isinstance(val, dict) and "rows" in val:
            return val["rows"]
        return val
    except json.JSONDecodeError:
        return [json.loads(l) for l in text.splitlines() if l.strip()]


def build156c(extra: dict) -> object:
    cfg = copy.deepcopy(L156c.DEFAULT_CONFIG156c)
    cfg.update(extra)
    return L156c.build_agent156c(cfg)


def new_daemon156c(root: Path):
    cfg = copy.deepcopy(L156c.DEFAULT_CONFIG156c)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L156c.Loop156cDaemon(root, cfg=cfg, idle_seconds=3600.0)


def moves_vs(rows: list[dict], base: list[dict], tag: str):
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r.get("verdict") != b.get("verdict"):
            moves.append({"id": r["id"], "base": b.get("verdict"),
                          tag: r.get("verdict"),
                          "reply_base": str(b.get("reply", ""))[:120],
                          "reply156c": str(r.get("reply", ""))[:120]})
            if r.get("verdict") in ("WRONG-WRITE", "WRONG-ANSWER", "WRONG",
                                    "WRONG-REPLY"):
                new_wrong += 1
    return moves, new_wrong


def reply_moves_vs(rows: list[dict], base: list[dict]):
    b_by_id = {r["id"]: r for r in base}
    return [r["id"] for r in rows
            if r["id"] in b_by_id
            and str(r.get("reply", "")) != str(b_by_id[r["id"]].get("reply", ""))]


def run_redteam136() -> dict:
    import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
    R136.new_daemon139b = new_daemon156c  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    (ART / "redteam136-loop156c.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    base = read_rows(ART138H / "redteam136-loop138h.json")
    moves, new_wrong = moves_vs(rows, base, "loop156c")
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r.get("verdict") for r in rows)),
            "moves_vs_138h": moves, "new_wrong_vs_138h": new_wrong,
            "reply_moves_vs_138h": reply_moves_vs(rows, base)}


def run_rt143() -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    R143.Loop132Daemon = L156c.Loop156cDaemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L156c.DEFAULT_CONFIG156c)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop156c"
    if scratch.exists():
        shutil.rmtree(scratch)
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = R143.run_case(case, scratch / case["id"], markers)
        rows.append(rec)
    (ART / "redteam143-loop156c.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base = read_rows(ART138H / "redteam143-loop138h.json")
    moves, new_wrong = moves_vs(rows, base, "loop156c")
    return {"suite": "rt143", "n": len(rows),
            "counter": dict(Counter(r.get("verdict") for r in rows)),
            "moves_vs_138h": moves, "new_wrong_vs_138h": new_wrong,
            "reply_moves_vs_138h": reply_moves_vs(rows, base)}


def run_sessions() -> dict:
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop156c" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L156c.DEFAULT_CONFIG156c)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L156c.Loop156cDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (ART / "sessions152-loop156c.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    out138h = json.loads(
        (ART138H / "sessions152-loop138h.json").read_text(encoding="utf-8"))
    moves, new_wrong, new_writes, reply_moves = [], 0, [], []
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, out138h.get(sid, [])):
            if t["verdict"] != b["verdict"]:
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138h": b["verdict"],
                              "loop156c": t["verdict"]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
            if str(t.get("reply", "")) != str(b.get("reply", "")):
                reply_moves.append({"session": sid, "n": t["n"]})
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"]})
    return {"suite": "sessions", "moves_vs_138h": moves,
            "new_wrong_vs_138h": new_wrong,
            "reply_moves_vs_138h": reply_moves, "new_writes": new_writes}


def run_bench(only: str = "all") -> dict:
    import fable_bench121_run as B  # noqa: E402 (scorer, read-only)
    B.Loop121Daemon = L156c.Loop156cDaemon
    cfg = copy.deepcopy(L156c.DEFAULT_CONFIG156c)
    cfg["sleep_threshold"] = 100000
    tag = "loop156c"
    DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
    DATA132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"
    splits = (
        ("new_121_4hop", B.DATA_NEW,
         "fable_bench121_loop138h_new_121_4hop_rows.jsonl"),
        ("old_s2fresh_4hop", B.DATA_OLD,
         "fable_bench121_loop138h_old_s2fresh_4hop_rows.jsonl"),
        ("edit200", DATA134, "fable_bench121_loop138h_edit200_rows.jsonl"),
        ("bench132_4hop", DATA132,
         "fable_bench121_loop138h_bench132_4hop_rows.jsonl"),
    )
    want = only.split(",")
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = ART / "scratch-bench121-loop156c"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    summary: dict = {"seconds": 0.0, "scorer": "v2", "agent": tag,
                     "splits": {}}
    t0 = time.time()
    for stag, path, sealed_name in splits:
        items = [json.loads(line) for line in
                 Path(str(path)).read_text(
                     encoding="utf-8").splitlines() if line.strip()]
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
        base_l = read_rows(ART138H / sealed_name)
        s_by_id = {r["id"]: r for r in base_l}
        moves, new_wrong = [], 0
        for r in rows:
            b = s_by_id.get(r["id"])
            if b is None:
                continue
            if r["verdict"] != b["verdict"]:
                moves.append({"id": r["id"], "base": b["verdict"],
                              "loop156c": r["verdict"]})
                if r["verdict"] == "wrong" and b["verdict"] != "wrong":
                    new_wrong += 1
        reply_moves = [r["id"] for r in rows if r["id"] in s_by_id
                       and str(r.get("reply", ""))
                       != str(s_by_id[r["id"]].get("reply", ""))]
        summary["splits"][stag] = {**cell, "moves_vs_138h": moves,
                                   "new_wrong_vs_138h": new_wrong,
                                   "reply_moves_vs_138h": reply_moves,
                                   "table": table}
        print(f"{tag} {stag}: {cell} moves={len(moves)} "
              f"new_wrong={new_wrong} reply_moves={len(reply_moves)}",
              flush=True)
    summary["seconds"] = round(time.time() - t0, 1)
    (ART / "bench156c-summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    shutil.rmtree(workroot, ignore_errors=True)
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 156c S3 suites")
    ap.add_argument("--only", default="all")
    args = ap.parse_args(argv)
    only = args.only
    t0 = time.time()
    out: dict = {}
    if only in ("junk", "all"):
        rep = run_redteam136()
        out[rep["suite"]] = rep
        print(f"S3 {rep['suite']}: n={rep['n']} {rep['counter']} "
              f"moves={len(rep['moves_vs_138h'])} "
              f"new_wrong={rep['new_wrong_vs_138h']} "
              f"reply_moves={len(rep['reply_moves_vs_138h'])}", flush=True)
    if only in ("rt143", "all"):
        rep = run_rt143()
        out[rep["suite"]] = rep
        print(f"S3 {rep['suite']}: n={rep['n']} {rep['counter']} "
              f"moves={len(rep['moves_vs_138h'])} "
              f"new_wrong={rep['new_wrong_vs_138h']} "
              f"reply_moves={len(rep['reply_moves_vs_138h'])}", flush=True)
    if only in ("sessions", "all"):
        rep = run_sessions()
        out[rep["suite"]] = rep
        print(f"S3 sessions: moves={len(rep['moves_vs_138h'])} "
              f"new_wrong={rep['new_wrong_vs_138h']} "
              f"reply_moves={len(rep['reply_moves_vs_138h'])} "
              f"new_writes={len(rep['new_writes'])}", flush=True)
    if only in ("bench", "all"):
        rep = run_bench()
        out["bench"] = rep
        print(f"S3 bench done seconds={rep['seconds']}", flush=True)
    wall = round(time.time() - t0, 1)
    out["wall_seconds"] = wall
    (ART / f"suites156c-{only}.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"TOTAL {wall} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
