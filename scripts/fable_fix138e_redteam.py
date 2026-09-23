#!/usr/bin/env python3
"""Exp 138e G3b driver -- redteam143 + sessions152 through the 138e agent.

Mirrors the scripts/fable_loop138b_redteam143.py /
scripts/fable_loop138b_sessions.py patterns (same sealed cases, judges,
mailbox harness imported read-only); only the daemon under test is
Loop138eDaemon (idle_seconds set explicitly). Compares per-case against
the FROZEN loop138b outputs in artifacts/fable-agent138b-20260922/
(read-only). Outputs into artifacts/fable-officechain138e-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138e_redteam.py [--only 143|--
sessions]
"""

from __future__ import annotations

import argparse
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

import fable_loop138e_agent as L138e  # noqa: E402 (agent under test)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)
import fable_session152_run as S152R  # noqa: E402 (sessions + judge)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-officechain138e-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"


def run_143() -> tuple[dict, int]:
    R143.Loop132Daemon = L138e.Loop138eDaemon  # type: ignore[method-assign]
    base_cfg = copy.deepcopy(L138e.DEFAULT_CONFIG138E)
    base_cfg["sleep_threshold"] = 100000
    R143.DEFAULT_CONFIG132 = copy.deepcopy(base_cfg)  # type: ignore[method-assign]
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop138e"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = R143.run_case(case, scratch / case["id"], markers)
        rows.append(rec)
    (ART / "redteam143-loop138e.json").write_text(
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
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "family": r.get("family"),
                          "loop138b": b["verdict"], "loop138e": r["verdict"],
                          "reply138b": str(b.get("reply", ""))[:120],
                          "reply138e": str(r.get("reply", ""))[:120]})
            if r["verdict"] == "WRONG-ANSWER" and b["verdict"] \
                    != "WRONG-ANSWER":
                new_wrong += 1
    out = {"loop138b": dict(Counter(r["verdict"] for r in frozen)),
           "loop138e": dict(Counter(r["verdict"] for r in rows)),
           "new_wrong_vs_loop138b": new_wrong, "moves": moves}
    (ART / "redteam143-compare138e.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G3b 143: loop138b {out['loop138b']} loop138e {out['loop138e']} "
          f"new_wrong={new_wrong} moves={len(moves)}", flush=True)
    for m in moves:
        print(f"  MOVE {m['id']} [{m['family']}]: "
              f"{m['loop138b']} -> {m['loop138e']}", flush=True)
    return out, (1 if new_wrong else 0)


def run_sessions() -> tuple[dict, int]:
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop138e" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L138e.DEFAULT_CONFIG138E)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L138e.Loop138eDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (ART / "sessions152-loop138e.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    frozen = json.loads((ART138B / "sessions152-loop138b.json").read_text(
        encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, 0
    for sid, turns in sessions_out.items():
        base_turns = {t.get("turn", i): t for i, t in
                      enumerate(frozen.get(sid, []))}
        for i, t in enumerate(turns):
            b = base_turns.get(t.get("turn", i))
            if b is None:
                continue
            if t["verdict"] != b.get("verdict"):
                moves.append({"session": sid, "turn": t.get("turn", i),
                              "loop138b": b.get("verdict"),
                              "loop138e": t["verdict"],
                              "reply138b": str(b.get("reply", ""))[:120],
                              "reply138e": str(t.get("reply", ""))[:120]})
                if t["verdict"] == "WRONG" and b.get("verdict") != "WRONG":
                    new_wrong += 1
            bw = len(b.get("writes", []) or [])
            gw = len(t.get("writes", []) or [])
            if gw > bw:
                new_writes += gw - bw
                moves.append({"session": sid, "turn": t.get("turn", i),
                              "new_writes": gw - bw})
    out = {"moves": moves, "new_wrong": new_wrong,
           "new_writes": new_writes}
    (ART / "sessions152-compare138e.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G3b sessions: moves={len(moves)} new_wrong={new_wrong} "
          f"new_writes={new_writes}", flush=True)
    for m in moves:
        print(f"  MOVE {m}", flush=True)
    return out, (1 if (new_wrong or new_writes) else 0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138e G3b redteam/sessions")
    ap.add_argument("--only", default="all", choices=("all", "143",
                                                      "sessions"))
    args = ap.parse_args(argv)
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    if args.only in ("all", "143"):
        _out, rc143 = run_143()
        rc |= rc143
    if args.only in ("all", "sessions"):
        _out, rcs = run_sessions()
        rc |= rcs
    print(f"G3b {round(time.time() - t0, 1)}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
