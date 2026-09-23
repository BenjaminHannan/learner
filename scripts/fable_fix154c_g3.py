#!/usr/bin/env python3
"""Experiment 154c -- G3 driver: redteam136 + redteam143 + sessions152.

Reuses BY IMPORT (read-only, nothing edited):
  * scripts/fable_fix139b_redteam136.run_case139b (daemon factory swapped
    to Loop154cDaemon, same pattern as the 154b G3 driver),
  * scripts/fable_redteam143_run (Loop132Daemon/DEFAULT_CONFIG132
    repointed, same pattern as the 154b driver),
  * scripts/fable_session152_run (sessions + judge, target swapped).
Compares per-case/turn against the FROZEN loop138b rows in
artifacts/fable-agent138b-20260922/. Bar: 0 moves, 0 new WRONG/WRONG-WRITE,
0 new junk writes. Outputs into artifacts/fable-multival154c-20260922/g3/.

Run (Mac CPU, offline; PASSMARKS sealed before any registered run):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_fix154c_g3.py
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
import fable_loop154c_agent as L154c  # noqa: E402 (agent under test)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)
import fable_session152_run as S152R  # noqa: E402 (sessions + judge)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-multival154c-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
OUT = ART / "g3"


def base_cfg() -> dict:
    cfg = json.loads((ART / "loop154c-config.json").read_text(
        encoding="utf-8"))
    cfg["sleep_threshold"] = 100000
    return cfg


def new_daemon154c(root: Path):
    cfg = base_cfg()
    cfg["state_dir"] = str(root)
    return L154c.Loop154cDaemon(root, cfg=cfg, idle_seconds=30.0)


def run_redteam136() -> dict:
    R136.new_daemon139b = new_daemon154c  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = OUT / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    (OUT / "redteam136-loop154c.json").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in rows) + "\n", encoding="utf-8")
    frozen = [json.loads(l) for l in
              (ART138B / "redteam136-loop138b.json").read_text(
                  encoding="utf-8").splitlines() if l.strip()]
    b_by_id = {r["id"]: r for r in frozen}
    moves, new_wrong, new_writes = [], 0, 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"] or \
                str(r.get("reply", "")) != str(b.get("reply", "")):
            moves.append({"id": r["id"], "loop138b": b["verdict"],
                          "loop154c": r["verdict"],
                          "reply138b": str(b.get("reply", ""))[:120],
                          "reply154c": str(r.get("reply", ""))[:120]})
            if str(r["verdict"]) in ("WRONG-WRITE", "WRONG") and \
                    str(b["verdict"]) not in ("WRONG-WRITE", "WRONG"):
                new_wrong += 1
        if int(r.get("facts_written", 0) or 0) > \
                int(b.get("facts_written", 0) or 0):
            new_writes += 1
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_138b": new_wrong, "new_writes": new_writes,
            "moves": moves}


def run_redteam143() -> dict:
    R143.Loop132Daemon = L154c.Loop154cDaemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = base_cfg()  # type: ignore[method-assign]
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = OUT / "scratch143-loop154c"
    rows = []
    for case in suite["cases"]:
        rows.append(R143.run_case(case, scratch / case["id"], markers))
    (OUT / "redteam143-loop154c.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    frozen = json.loads((ART138B / "redteam143-loop138b.json").read_text(
        encoding="utf-8"))["rows"]
    b_by_id = {r["id"]: r for r in frozen}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"] or \
                str(r.get("reply", "")) != str(b.get("reply", "")):
            moves.append({"id": r["id"], "family": r.get("family"),
                          "loop138b": b["verdict"],
                          "loop154c": r["verdict"],
                          "reply138b": str(b.get("reply", ""))[:120],
                          "reply154c": str(r.get("reply", ""))[:120]})
            if r["verdict"] == "WRONG-ANSWER" and \
                    b["verdict"] != "WRONG-ANSWER":
                new_wrong += 1
    return {"suite": "redteam143", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_138b": new_wrong, "moves": moves}


def run_sessions() -> dict:
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = OUT / "work-sessions-loop154c" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = base_cfg()
        cfg["state_dir"] = str(root)
        daemon = L154c.Loop154cDaemon(root, cfg=cfg, idle_seconds=30.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (OUT / "sessions152-loop154c.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    frozen = json.loads((ART138B / "sessions152-loop138b.json").read_text(
        encoding="utf-8"))
    moves, new_wrong = [], 0
    counts: Counter = Counter()
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, frozen.get(sid, [])):
            counts[t["verdict"]] += 1
            if t["verdict"] != b["verdict"] or \
                    str(t.get("reply", "")).strip() != \
                    str(b.get("reply", "")).strip():
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138b": b["verdict"],
                              "loop154c": t["verdict"],
                              "reply138b": str(b["reply"]).strip()[:120],
                              "reply154c": str(t["reply"]).strip()[:120]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
    return {"suite": "sessions152", "n_sessions": len(sessions_out),
            "counter": dict(counts), "new_wrong_vs_138b": new_wrong,
            "moves": moves}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out: dict = {}
    rc = 0
    for fn in (run_redteam136, run_redteam143, run_sessions):
        rep = fn()
        out[rep["suite"]] = rep
        print(f"G3 {rep['suite']}: n={rep.get('n', rep.get('n_sessions'))} "
              f"counter={rep.get('counter')} "
              f"new_wrong={rep['new_wrong_vs_138b']} "
              f"moves={len(rep['moves'])}", flush=True)
        for m in rep["moves"]:
            print(f"  MOVE {m.get('id', m.get('session'))}: "
                  f"{m.get('loop138b')} -> {m.get('loop154c')}", flush=True)
        if rep["new_wrong_vs_138b"] or len(rep["moves"]):
            rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    (OUT / "g3-summary.json").write_text(
        json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    print(f"G3 done in {out['seconds']}s", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
