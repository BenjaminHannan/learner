#!/usr/bin/env python3
"""Experiment 190 -- V2 frozen-suite driver (Muse).

Runs redteam136 (145 cases), redteam143 (124 cases), sessions152 (180
turns) through loop190 (fresh in-process loops / Loop190Daemon with
idle_seconds, sleep_threshold=100000) and compares per-case against the
SEALED loop138g rows in artifacts/fable-agent138g-20260922/ (read-only).
Predicts ZERO moves (pre-seal static scan: no frozen-suite turn matches
the closed 190 shapes; see PASSMARKS.md). Any move fails honestly.
Outputs into artifacts/fable-reverse190-20260922/ only.

marks123 runs separately via scripts/fable_marks123_all.py --agent
scripts/fable_loop190_agent.py (one suite at a time) + the compare step
in scripts/fable_fix190_marks.py.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; one suite at
a time under parallel-agent load):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix190_suites.py --only junk|rt143|sessions|all
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
import fable_loop190_agent as L190  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-reverse190-20260922"
ART138G = ROOT / "artifacts" / "fable-agent138g-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"


def build190(extra: dict) -> object:
    cfg = copy.deepcopy(L190.DEFAULT_CONFIG190)
    cfg.update(extra)
    return L190.build_agent190(cfg)


def new_daemon190(root: Path):
    cfg = copy.deepcopy(L190.DEFAULT_CONFIG190)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L190.Loop190Daemon(root, cfg=cfg, idle_seconds=3600.0)


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
                          "reply190": str(r.get("reply", ""))[:120]})
            if r["verdict"] in ("WRONG-WRITE", "WRONG-ANSWER", "WRONG",
                                "WRONG-REPLY", "WRONG"):
                new_wrong += 1
    return moves, new_wrong


def run_redteam136() -> dict:
    R136.new_daemon139b = new_daemon190  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136-190"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows(ART / "redteam136-loop190.json", rows)
    sealed = [json.loads(l) for l in
              (ART138G / "redteam136-loop138g.json").read_text(
                  encoding="utf-8").splitlines() if l.strip()]
    moves, new_wrong = moves_vs(rows, sealed, "loop190")
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138g": moves, "new_wrong_vs_138g": new_wrong}


def run_rt143() -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    R143.Loop132Daemon = L190.Loop190Daemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L190.DEFAULT_CONFIG190)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop190"
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = R143.run_case(case, scratch / case["id"], markers)
        rows.append(rec)
    (ART / "redteam143-loop190.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base = json.loads(
        (ART138G / "redteam143-loop138g.json").read_text(encoding="utf-8"))
    moves, new_wrong = moves_vs(rows, base["rows"], "loop190")
    return {"suite": "rt143",
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138g": moves, "new_wrong_vs_138g": new_wrong}


def run_sessions() -> dict:
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop190" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L190.DEFAULT_CONFIG190)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L190.Loop190Daemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (ART / "sessions152-loop190.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    out138g = json.loads(
        (ART138G / "sessions152-loop138g.json").read_text(encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, []
    counts138g: Counter = Counter()
    counts190: Counter = Counter()
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, out138g.get(sid, [])):
            counts138g[b["verdict"]] += 1
            counts190[t["verdict"]] += 1
            reply_same = (str(t.get("reply", "")).strip()
                          == str(b.get("reply", "")).strip())
            if t["verdict"] != b["verdict"] or not reply_same:
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138g": b["verdict"],
                              "loop190": t["verdict"],
                              "reply138g": str(b["reply"]).strip()[:120],
                              "reply190": str(t["reply"]).strip()[:120],
                              "why": t["why"][:160]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"],
                                   "loop138g_writes": bw,
                                   "loop190_writes": tw})
    return {"suite": "sessions", "loop138g": dict(counts138g),
            "loop190": dict(counts190),
            "new_wrong_vs_138g": new_wrong, "moves_vs_138g": moves,
            "new_writes": new_writes}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 190 V2 frozen suites")
    ap.add_argument("--only", default="all",
                    help="comma list of rt136,rt143,sessions or all")
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
              f"moves={len(out['rt136']['moves_vs_138g'])} "
              f"new_wrong={out['rt136']['new_wrong_vs_138g']}", flush=True)
        for m in out["rt136"]["moves_vs_138g"]:
            print(f"  MOVE {m}", flush=True)
    if "all" in want or "rt143" in want:
        t1 = time.time()
        out["rt143"] = run_rt143()
        out["rt143"]["seconds"] = round(time.time() - t1, 1)
        print(f"V2 rt143: {out['rt143']['counter']} "
              f"moves={len(out['rt143']['moves_vs_138g'])} "
              f"new_wrong={out['rt143']['new_wrong_vs_138g']}", flush=True)
        for m in out["rt143"]["moves_vs_138g"]:
            print(f"  MOVE {m}", flush=True)
    if "all" in want or "sessions" in want:
        t1 = time.time()
        out["sessions"] = run_sessions()
        out["sessions"]["seconds"] = round(time.time() - t1, 1)
        print(f"V2 sessions: 138g {out['sessions']['loop138g']} 190 "
              f"{out['sessions']['loop190']} new_wrong="
              f"{out['sessions']['new_wrong_vs_138g']} "
              f"new_writes={len(out['sessions']['new_writes'])} "
              f"moves={len(out['sessions']['moves_vs_138g'])}", flush=True)
        for m in out["sessions"]["moves_vs_138g"]:
            print(f"  MOVE {m['session']}#{m['n']} {m['text']!r}: "
                  f"{m['loop138g']} -> {m['loop190']}", flush=True)
    (ART / "v2-frozen-summary190.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    out["seconds"] = round(time.time() - t0, 1)
    print(f"V2 frozen done in {out['seconds']}s", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
