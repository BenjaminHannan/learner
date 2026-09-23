#!/usr/bin/env python3
"""Exp 171 G3 driver -- junk/redteam/sessions suites through loop171.

Reuses the 138d folder's drivers BY IMPORT with only the agent swapped:
  redteam136/cases150/f1/cases139b: scripts/fable_loop138d_junk.run_* (its
    sealed judges fable_fix139b_redteam136 / fable_fix139b_probe /
    fable_fix150_probe); build/new_daemon/ART patched to the 171 arm.
  redteam143: scripts/fable_loop138d_redteam143.run_arm (sealed cases +
    judge in fable_redteam143_run).
  sessions152: scripts/fable_loop138d_sessions.run_target (sealed sessions
    + judge in fable_session152_run).
All comparisons are per-case/per-turn against the SEALED loop138b frozen
rows in artifacts/fable-agent138b-20260922/ (read-only). Bar: 0 new WRONG /
WRONG-WRITE / junk writes vs loop138b; every move predicted in writing
before the run. Outputs into artifacts/fable-nameval171-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix171_g3.py
"""

from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138d_junk as J138d  # noqa: E402 (junk suites, reuse)
import fable_loop138d_redteam143 as R143D  # noqa: E402 (rt143 arm, reuse)
import fable_loop138d_sessions as S152D  # noqa: E402 (sessions arm, reuse)
import fable_loop171_agent as L171  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-nameval171-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"

RENAMES = {
    "redteam136-loop138d.json": "redteam136-loop171.json",
    "probe150-loop138d.json": "probe150-loop171.json",
    "f1-loop138d.json": "f1-loop171.json",
    "probe139b-loop138d.json": "probe139b-loop171.json",
}


def build171(extra: dict) -> object:
    cfg = copy.deepcopy(L171.DEFAULT_CONFIG171)
    cfg.update(extra)
    return L171.build_agent171(cfg)


def new_daemon171(root: Path):
    cfg = copy.deepcopy(L171.DEFAULT_CONFIG171)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L171.Loop171Daemon(root, cfg=cfg, idle_seconds=3600.0)


def run_junk() -> dict:
    J138d.build138b = build171  # type: ignore[method-assign]
    J138d.new_daemon138b = new_daemon171  # type: ignore[method-assign]
    J138d.ART = ART
    out: dict = {}
    for fn in (J138d.run_redteam136, J138d.run_cases150, J138d.run_f1,
               J138d.run_cases139b):
        rep = fn()
        out[rep["suite"]] = rep
    for src, dst in RENAMES.items():
        p = ART / src
        if p.exists():
            p.replace(ART / dst)
    if (ART / "junk138d-summary.json").exists():
        (ART / "junk138d-summary.json").replace(
            ART / "junk171-suites.json")
    (ART / "junk171-suites.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    return out


def run_rt143() -> dict:
    cfg171 = copy.deepcopy(L171.DEFAULT_CONFIG171)
    cfg171["sleep_threshold"] = 100000
    R143D.ART = ART
    rows171 = R143D.run_arm("loop171", L171.Loop171Daemon, cfg171)
    (ART / "redteam143-loop171.json").write_text(
        json.dumps({"seconds": 0, "rows": rows171}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    rows138b = json.loads(
        (ART138B / "redteam143-loop138b.json").read_text(
            encoding="utf-8"))["rows"]
    b_by_id = {r["id"]: r for r in rows138b}
    moves, new_wrong = [], 0
    for r in rows171:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "family": r.get("family"),
                          "loop138b": b["verdict"], "loop171": r["verdict"],
                          "reply138b": str(b.get("reply", ""))[:160],
                          "reply171": str(r.get("reply", ""))[:160],
                          "reasons": r.get("reasons", [])})
            if (r["verdict"] == "WRONG-ANSWER"
                    and b["verdict"] != "WRONG-ANSWER"):
                new_wrong += 1
    return {"loop138b": dict(Counter(r["verdict"] for r in rows138b)),
            "loop171": dict(Counter(r["verdict"] for r in rows171)),
            "new_wrong_vs_loop138b": new_wrong, "moves": moves}


def run_sessions() -> dict:
    cfg171 = copy.deepcopy(L171.DEFAULT_CONFIG171)
    cfg171["sleep_threshold"] = 100000
    S152D.ART = ART
    out171 = S152D.run_target("loop171", L171.Loop171Daemon, cfg171)
    (ART / "sessions152-loop171.json").write_text(
        json.dumps(out171, indent=1, ensure_ascii=False), encoding="utf-8")
    out138b = json.loads(
        (ART138B / "sessions152-loop138b.json").read_text(encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, []
    counts138b: Counter = Counter()
    counts171: Counter = Counter()
    for sid, turns in out171.items():
        for t, b in zip(turns, out138b.get(sid, [])):
            counts138b[b["verdict"]] += 1
            counts171[t["verdict"]] += 1
            if t["verdict"] != b["verdict"]:
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138b": b["verdict"],
                              "loop171": t["verdict"],
                              "reply138b": str(b["reply"]).strip()[:160],
                              "reply171": str(t["reply"]).strip()[:160],
                              "why": t["why"][:160]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"],
                                   "loop138b_writes": bw,
                                   "loop171_writes": tw})
    return {"loop138b": dict(counts138b), "loop171": dict(counts171),
            "new_wrong_vs_loop138b": new_wrong, "moves": moves,
            "new_writes": new_writes}


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    out: dict = {}
    out["junk"] = run_junk()
    for suite, rep in out["junk"].items():
        movekeys = [k for k in rep if k.startswith("move") or k == "non_ok"]
        nmoves = sum(len(rep.get(k, []) or []) for k in movekeys)
        print(f"G3 {suite}: n={rep['n']} {rep['counter']} moved={nmoves}",
              flush=True)
        for key in ("moves", "moves_vs_loop138b", "non_ok"):
            for m in rep.get(key, []) or []:
                print(f"  {key} {m}", flush=True)
        if rep.get("new_wrong_vs_138b"):
            rc = 1
        for key in ("moves", "moves_vs_loop138b"):
            for m in rep.get(key, []) or []:
                if m.get("loop138d", "") in ("WRONG-WRITE", "WRONG-ANSWER",
                                             "WRONG-REPLY", "WRONG"):
                    rc = 1
    out["redteam143"] = run_rt143()
    print(f"G3 143: loop138b {out['redteam143']['loop138b']} loop171 "
          f"{out['redteam143']['loop171']} "
          f"new_wrong={out['redteam143']['new_wrong_vs_loop138b']} "
          f"moves={len(out['redteam143']['moves'])}", flush=True)
    for m in out["redteam143"]["moves"]:
        print(f"  MOVE {m['id']} [{m['family']}]: "
              f"{m['loop138b']} -> {m['loop171']}", flush=True)
    if out["redteam143"]["new_wrong_vs_loop138b"]:
        rc = 1
    out["sessions"] = run_sessions()
    print(f"G3 sessions: loop138b {out['sessions']['loop138b']} loop171 "
          f"{out['sessions']['loop171']} "
          f"new_wrong={out['sessions']['new_wrong_vs_loop138b']} "
          f"new_writes={len(out['sessions']['new_writes'])} "
          f"moves={len(out['sessions']['moves'])}", flush=True)
    for m in out["sessions"]["moves"]:
        print(f"  MOVE {m['session']}#{m['n']} {m['text']!r}: "
              f"{m['loop138b']} -> {m['loop171']}", flush=True)
    for m in out["sessions"]["new_writes"]:
        print(f"  NEWW {m}", flush=True)
        rc = 1
    if out["sessions"]["new_wrong_vs_loop138b"]:
        rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    (ART / "sessions152-compare171.json").write_text(
        json.dumps({"seconds": out["seconds"],
                    "sessions": out["sessions"],
                    "redteam143": out["redteam143"]},
                   indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    print(f"G3 {out['seconds']}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
