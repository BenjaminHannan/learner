#!/usr/bin/env python3
"""Experiment 139c G3 -- junk + redteam + sessions through loop139c.

Three suites, each judged by its sealed judge imported read-only, each
case through a FRESH loop139c; compared per-case against the SEALED
loop138b rows in artifacts/fable-agent138b-20260922/ (not re-running
loop138b). Bar: 0 new WRONG/WRONG-WRITE vs loop138b, every move predicted
in writing before the run (PASSMARKS.md predicts 0 moves).

  redteam136: 145 sealed cases (scripts/fable_fix139b_redteam136 pattern:
    new_daemon139b repointed to Loop139cDaemon) vs redteam136-loop138b.json.
  redteam143: scripts/fable_redteam143_run pattern (Loop132Daemon /
    DEFAULT_CONFIG132 repointed) vs redteam143-loop138b.json.
  sessions152: scripts/fable_loop138b_sessions.py run_target pattern vs
    sessions152-loop138b.json.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix139c_g3.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
import fable_loop139c_agent as L139c  # noqa: E402 (agent under test)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)
import fable_session152_run as S152R  # noqa: E402 (sessions + judge)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-tailwords139c-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"


def new_daemon139c(root: Path):
    cfg = copy.deepcopy(L139c.DEFAULT_CONFIG139C)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L139c.Loop139cDaemon(root, cfg=cfg, idle_seconds=3600.0)


def run_redteam136() -> dict:
    R136.new_daemon139b = new_daemon139c  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(encoding="utf-8"))
    workroot = ART / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    (ART / "redteam136-loop139c.json").write_text(
        json.dumps({"rows": rows}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    base_rows = [json.loads(line) for line in
                 (ART138B / "redteam136-loop138b.json").read_text(
                     encoding="utf-8").splitlines() if line.strip()]
    b_by_id = {r["id"]: r for r in base_rows}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "loop138b": b["verdict"],
                          "loop139c": r["verdict"],
                          "reply138b": str(b.get("reply", ""))[:120],
                          "reply139c": str(r.get("reply", ""))[:120]})
            if r["verdict"] == "WRONG-WRITE" and \
                    b["verdict"] != "WRONG-WRITE":
                new_wrong += 1
    return {"counts139c": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_loop138b": new_wrong, "moves": moves}


def run_redteam143() -> dict:
    R143.Loop132Daemon = L139c.Loop139cDaemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L139c.DEFAULT_CONFIG139C)
    R143.DEFAULT_CONFIG132["sleep_threshold"] = 100000
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop139c"
    rows = [R143.run_case(case, scratch / case["id"], markers)
            for case in suite["cases"]]
    (ART / "redteam143-loop139c.json").write_text(
        json.dumps({"rows": rows}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    base = json.loads((ART138B / "redteam143-loop138b.json").read_text(
        encoding="utf-8"))
    b_by_id = {r["id"]: r for r in base["rows"]}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "loop138b": b["verdict"],
                          "loop139c": r["verdict"],
                          "reply138b": str(b.get("reply", ""))[:120],
                          "reply139c": str(r.get("reply", ""))[:120]})
            if r["verdict"] == "WRONG-ANSWER" and \
                    b["verdict"] != "WRONG-ANSWER":
                new_wrong += 1
    return {"counts139c": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_loop138b": new_wrong, "moves": moves}


def run_sessions() -> dict:
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop139c" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L139c.DEFAULT_CONFIG139C)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L139c.Loop139cDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (ART / "sessions152-loop139c.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    base = json.loads((ART138B / "sessions152-loop138b.json").read_text(
        encoding="utf-8"))
    moves, new_wrong = [], 0
    counts: Counter = Counter()
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, base.get(sid, [])):
            counts[t["verdict"]] += 1
            if t["verdict"] != b["verdict"]:
                moves.append({"session": sid, "n": t["n"],
                              "loop138b": b["verdict"],
                              "loop139c": t["verdict"],
                              "reply138b": str(b["reply"]).strip()[:120],
                              "reply139c": str(t["reply"]).strip()[:120]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
    return {"counts139c": dict(counts),
            "new_wrong_vs_loop138b": new_wrong, "moves": moves}


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    r136 = run_redteam136()
    r143 = run_redteam143()
    s152 = run_sessions()
    out = {"seconds": round(time.time() - t0, 1), "redteam136": r136,
           "redteam143": r143, "sessions152": s152}
    (ART / "g3-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    rc = 0
    for name, r in (("redteam136", r136), ("redteam143", r143),
                    ("sessions152", s152)):
        print(f"G3 {name}: {r['counts139c']} "
              f"new_wrong={r['new_wrong_vs_loop138b']} "
              f"moves={len(r['moves'])}", flush=True)
        for m in r["moves"]:
            print(f"  MOVE {m}", flush=True)
        if r["new_wrong_vs_loop138b"] != 0:
            rc = 1
    print(f"G3 {out['seconds']}s -> {ART / 'g3-compare.json'}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
