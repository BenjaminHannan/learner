#!/usr/bin/env python3
"""Experiment 190b -- V2 frozen suites + V3 bench drivers (Muse).

Runs redteam136 (145 cases), redteam143 (124 cases), sessions152 (180
turns), and bench121's 4 splits through loop190b (fresh in-process
loops / Loop190bDaemon with idle_seconds, sleep_threshold=100000) and
compares per-case against the SEALED loop190 rows in
artifacts/fable-reverse190-20260922/ (read-only). Predicts ZERO moves:
190b differs from 190 only on closed-shape (E1-E4) reverse no-match
turns whose value is unknown, and the 190 pre-seal static scan found 0
frozen/bench turns matching the closed shapes at all (see PASSMARKS).
Any move fails honestly. Outputs into
artifacts/fable-reverse190b-20260922/ only.

marks123 runs separately via scripts/fable_marks123_all.py --agent
scripts/fable_loop190b_agent.py (one suite at a time) + the compare
step in scripts/fable_fix190b_marks.py.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; one suite at
a time under parallel-agent load):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_fix190b_suites.py --only rt136|rt143|sessions|bench|all
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

import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
import fable_loop190b_agent as L190B  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-reverse190b-20260922"
ART190 = ROOT / "artifacts" / "fable-reverse190-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"


def new_daemon190b(root: Path):
    cfg = copy.deepcopy(L190B.DEFAULT_CONFIG190B)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L190B.Loop190bDaemon(root, cfg=cfg, idle_seconds=3600.0)


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                          sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def moves_vs(rows: list[dict], base: list[dict], tag: str) -> tuple[list, int]:
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        reply_same = (str(r.get("reply", "")).strip()
                      == str(b.get("reply", "")).strip())
        if r["verdict"] != b["verdict"] or not reply_same:
            moves.append({"id": r["id"], "base": b["verdict"],
                          tag: r["verdict"],
                          "reply_base": str(b.get("reply", ""))[:120],
                          "reply190b": str(r.get("reply", ""))[:120]})
            if r["verdict"] in ("WRONG-WRITE", "WRONG-ANSWER", "WRONG",
                                 "WRONG-REPLY", "WRONG"):
                new_wrong += 1
    return moves, new_wrong


def run_redteam136() -> dict:
    R136.new_daemon139b = new_daemon190b  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136-190b"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows(ART / "redteam136-loop190b.json", rows)
    sealed = [json.loads(l) for l in
              (ART190 / "redteam136-loop190.json").read_text(
                  encoding="utf-8").splitlines() if l.strip()]
    moves, new_wrong = moves_vs(rows, sealed, "loop190b")
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_190": moves, "new_wrong_vs_190": new_wrong}


def run_rt143() -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    R143.Loop132Daemon = L190B.Loop190bDaemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L190B.DEFAULT_CONFIG190B)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop190b"
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = R143.run_case(case, scratch / case["id"], markers)
        rows.append(rec)
    (ART / "redteam143-loop190b.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base = json.loads(
        (ART190 / "redteam143-loop190.json").read_text(encoding="utf-8"))
    moves, new_wrong = moves_vs(rows, base["rows"], "loop190b")
    return {"suite": "rt143",
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_190": moves, "new_wrong_vs_190": new_wrong}


def run_sessions() -> dict:
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop190b" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L190B.DEFAULT_CONFIG190B)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L190B.Loop190bDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (ART / "sessions152-loop190b.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    out190 = json.loads(
        (ART190 / "sessions152-loop190.json").read_text(encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, []
    counts190: Counter = Counter()
    counts190b: Counter = Counter()
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, out190.get(sid, [])):
            counts190[b["verdict"]] += 1
            counts190b[t["verdict"]] += 1
            reply_same = (str(t.get("reply", "")).strip()
                          == str(b.get("reply", "")).strip())
            if t["verdict"] != b["verdict"] or not reply_same:
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop190": b["verdict"],
                              "loop190b": t["verdict"],
                              "reply190": str(b["reply"]).strip()[:120],
                              "reply190b": str(t["reply"]).strip()[:120],
                              "why": t["why"][:160]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"],
                                   "loop190_writes": bw,
                                   "loop190b_writes": tw})
    return {"suite": "sessions", "loop190": dict(counts190),
            "loop190b": dict(counts190b),
            "new_wrong_vs_190": new_wrong, "moves_vs_190": moves,
            "new_writes": new_writes}


def run_bench(only: str = "all") -> dict:
    import fable_bench121_run as B  # noqa: E402 (scorer, read-only)
    import fable_fix190_reverse as R190  # noqa: E402 (parser, read-only)
    B.Loop121Daemon = L190B.Loop190bDaemon
    cfg = copy.deepcopy(L190B.DEFAULT_CONFIG190B)
    cfg["sleep_threshold"] = 100000
    tag = "loop190b"
    DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
    DATA132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"
    splits = (
        ("new_121_4hop", B.DATA_NEW,
         "fable_bench121_loop190_new_121_4hop_rows.jsonl"),
        ("old_s2fresh_4hop", B.DATA_OLD,
         "fable_bench121_loop190_old_s2fresh_4hop_rows.jsonl"),
        ("edit200", DATA134, "fable_bench121_loop190_edit200_rows.jsonl"),
        ("bench132_4hop", DATA132,
         "fable_bench121_loop190_bench132_4hop_rows.jsonl"),
    )
    want = only.split(",")
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = ART / "scratch-bench121-loop190b"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    summary: dict = {"seconds": 0.0, "scorer": "v2", "agent": tag,
                     "splits": {}}
    for stag, path, sealed_name in splits:
        items = [json.loads(line) for line in
                 Path(str(path)).read_text(
                     encoding="utf-8").splitlines() if line.strip()]
        rev_rows = [it.get("id", "?") for it in items
                    if R190.parse_reverse190(
                        it.get("question", it.get("text", ""))) is not None]
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
        base_rows_l = [json.loads(line) for line in
                       (ART190 / sealed_name).read_text(
                           encoding="utf-8").splitlines() if line.strip()]
        s_by_id = {r["id"]: r for r in base_rows_l}
        moves, new_wrong = [], 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                moves.append({"id": r["id"], "loop190": s["verdict"],
                              tag: r["verdict"]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        rev_report = [{"id": r["id"], "verdict": r["verdict"],
                       "reply": str(r.get("reply", ""))[:120]}
                      for r in rows if r["id"] in set(rev_rows)]
        summary["splits"][stag] = {tag: cell, "by_type": table,
                                   "moves_vs_190": moves,
                                   "new_wrong_vs_190": new_wrong,
                                   "reversal_rows_n": len(rev_rows),
                                   "reversal_rows": rev_report}
        print(f"{stag}: {tag} {cell} new_wrong={new_wrong} "
              f"moves={len(moves)} reversal_rows={len(rev_rows)}",
              flush=True)
        for m in moves:
            print(f"  MOVE {m}", flush=True)
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 190b V2+V3 suites")
    ap.add_argument("--only", default="all",
                    help="comma list of rt136,rt143,sessions,bench or all")
    ap.add_argument("--bench-only", default="all")
    args = ap.parse_args(argv)
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    want = args.only.split(",")
    out: dict = {}
    if "all" in want or "rt136" in want:
        t1 = time.time()
        out["rt136"] = run_redteam136()
        out["rt136"]["seconds"] = round(time.time() - t1, 1)
        print(f"V2 rt136: n={out['rt136']['n']} {out['rt136']['counter']} "
              f"moves={len(out['rt136']['moves_vs_190'])} "
              f"new_wrong={out['rt136']['new_wrong_vs_190']}", flush=True)
        for m in out["rt136"]["moves_vs_190"]:
            print(f"  MOVE {m}", flush=True)
    if "all" in want or "rt143" in want:
        t1 = time.time()
        out["rt143"] = run_rt143()
        out["rt143"]["seconds"] = round(time.time() - t1, 1)
        print(f"V2 rt143: {out['rt143']['counter']} "
              f"moves={len(out['rt143']['moves_vs_190'])} "
              f"new_wrong={out['rt143']['new_wrong_vs_190']}", flush=True)
        for m in out["rt143"]["moves_vs_190"]:
            print(f"  MOVE {m}", flush=True)
    if "all" in want or "sessions" in want:
        t1 = time.time()
        out["sessions"] = run_sessions()
        out["sessions"]["seconds"] = round(time.time() - t1, 1)
        print(f"V2 sessions: 190 {out['sessions']['loop190']} 190b "
              f"{out['sessions']['loop190b']} new_wrong="
              f"{out['sessions']['new_wrong_vs_190']} "
              f"new_writes={len(out['sessions']['new_writes'])} "
              f"moves={len(out['sessions']['moves_vs_190'])}", flush=True)
        for m in out["sessions"]["moves_vs_190"]:
            print(f"  MOVE {m['session']}#{m['n']} {m['text']!r}: "
                  f"{m['loop190']} -> {m['loop190b']}", flush=True)
    if "all" in want or "bench" in want:
        t1 = time.time()
        out["bench"] = run_bench(args.bench_only)
        out["bench"]["seconds"] = round(time.time() - t1, 1)
        print(f"V3 bench done in {out['bench']['seconds']}s", flush=True)
    (ART / "v2-frozen-summary190b.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    out["seconds"] = round(time.time() - t0, 1)
    print(f"V2+V3 done in {out['seconds']}s", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
