#!/usr/bin/env python3
"""Experiment 173b -- G3 sessions152 + redteam136/143 through loop173b.

Reuses sealed runners by import (read-only, never edited):
  sessions152: scripts/fable_session152_run.py run_session/judge
  redteam136: mailbox process_pending like the 136 runner
  redteam143: scripts/fable_redteam143_run.py run_case

Runs only the NEW agent (loop173b); the reference side is loop173's own
FROZEN rows in artifacts/fable-username173-20260922/ (redteam136-loop173,
redteam143-loop173, sessions152-loop173, read-only). Bar: 0 verdict moves,
0 reply moves, 0 new WRONG/WRONG-WRITE, 0 write moves (ZERO predicted:
pre-seal scan finds no 173b name-statement shape in any G3 input).

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix173b_g3.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix129_common as C129  # noqa: E402 (mailbox driver, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop173b_agent as L173B  # noqa: E402 (this experiment)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)
import fable_session152_run as S152R  # noqa: E402 (runner fns, read-only)

ROOT = SCRIPTS.parent
ART173 = ROOT / "artifacts" / "fable-username173-20260922"
ART173B = ROOT / "artifacts" / "fable-username173b-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"


def new_daemon(root: Path, idle: float = 3600.0):
    cfg = copy.deepcopy(L173B.DEFAULT_CONFIG173B)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L173B.Loop173bDaemon(root, cfg=cfg, idle_seconds=idle)


def run_136(workroot: Path) -> list[dict]:
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    rows = []
    for row in cases:
        root = Path(tempfile.mkdtemp(prefix=row["id"] + "_",
                                     dir=str(workroot)))
        (root / "inbox").mkdir(exist_ok=True)
        t0 = time.time()
        try:
            daemon = new_daemon(root)
        except Exception as exc:  # noqa: BLE001
            rows.append({"id": row["id"], "verdict": "HARNESS-ERROR",
                         "reply": f"BOOT-FAILED {exc!r}", "stored": []})
            continue
        (root / "inbox" / "msg_00.txt").write_text(row["text"],
                                                   encoding="utf-8")
        log: list = []
        try:
            C129.process_pending(daemon, root, log)
            stored = [list(t) for t in L90.notebook_triples(daemon.loop.nb)]
            reply = log[-1]["reply"] if log else "NO-LOG"
        except Exception as exc:  # noqa: BLE001
            rows.append({"id": row["id"], "verdict": "HARNESS-ERROR",
                         "reply": f"HARNESS-CAUGHT {exc!r}", "stored": []})
            continue
        exp = row["expect"]
        if exp == "nowrite":
            verdict = "OK" if not stored else "WRONG-WRITE"
        else:
            want = [list(exp)]
            if stored == want:
                verdict = "OK"
            elif not stored:
                verdict = "MISSED"
            else:
                verdict = "WRONG-WRITE"
        rows.append({"id": row["id"], "group": row["group"],
                     "verdict": verdict, "stored": stored, "reply": reply,
                     "seconds": round(time.time() - t0, 3)})
    return rows


def run_143(workroot: Path) -> list[dict]:
    R143.Loop132Daemon = L173B.Loop173bDaemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L173B.DEFAULT_CONFIG173B)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = workroot / "scratch143-loop173b"
    return [R143.run_case(c, scratch / c["id"], markers)
            for c in suite["cases"]]


def run_152(workroot: Path) -> list[dict]:
    sessions = json.loads((ART152 / "sessions152.json").read_text(
        encoding="utf-8"))
    turns_all = []
    for s in sessions:
        root = workroot / "s152-loop173b" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        daemon = new_daemon(root)
        turns = S152R.run_session(daemon, root, s)
        for t in turns:
            t.update(S152R.judge(t))
            t["session"] = s["id"]
        turns_all.extend(turns)
    return turns_all


def main() -> int:
    ART173B.mkdir(parents=True, exist_ok=True)
    work = ART173B / "scratch-g3"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / "rt136").mkdir(parents=True)
    (work / "rt143").mkdir(parents=True)
    (work / "s152").mkdir(parents=True)
    t0 = time.time()
    summary: dict = {}

    r136_new = run_136(work / "rt136")
    (ART173B / "redteam136-loop173b.json").write_text(
        json.dumps(r136_new, indent=1), encoding="utf-8")
    r136_base = json.loads((ART173 / "redteam136-loop173.json").read_text(
        encoding="utf-8"))
    b136 = {r["id"]: r for r in r136_base}
    m136 = [r["id"] for r in r136_new
            if b136.get(r["id"], {}).get("verdict") != r["verdict"]]
    rm136 = [r["id"] for r in r136_new
             if b136.get(r["id"], {}).get("reply") != r["reply"]]
    nw136 = [r["id"] for r in r136_new
             if r["verdict"] in ("WRONG-WRITE", "WRONG")
             and b136.get(r["id"], {}).get("verdict")
             not in ("WRONG-WRITE", "WRONG")]
    print(f"redteam136: n={len(r136_new)} verdict_moves={m136} "
          f"reply_moves={rm136} new_wrong={nw136}", flush=True)
    summary["redteam136"] = {"n": len(r136_new), "verdict_moves": m136,
                             "reply_moves": rm136, "new_wrong": nw136}

    r143_new = run_143(work / "rt143")
    (ART173B / "redteam143-loop173b.json").write_text(
        json.dumps(r143_new, indent=1), encoding="utf-8")
    r143_base = json.loads((ART173 / "redteam143-loop173.json").read_text(
        encoding="utf-8"))
    b143 = {r["id"]: r for r in r143_base}
    m143 = [r["id"] for r in r143_new
            if b143.get(r["id"], {}).get("verdict") != r["verdict"]]
    rm143 = [r["id"] for r in r143_new
             if b143.get(r["id"], {}).get("reply") != r["reply"]]
    nw143 = [r["id"] for r in r143_new
             if r["verdict"] not in ("OK",)
             and b143.get(r["id"], {}).get("verdict") in ("OK",)]
    print(f"redteam143: n={len(r143_new)} verdict_moves={m143} "
          f"reply_moves={rm143} new_bad={nw143}", flush=True)
    summary["redteam143"] = {"n": len(r143_new), "verdict_moves": m143,
                             "reply_moves": rm143, "new_bad": nw143}

    s152_new = run_152(work / "s152")
    (ART173B / "sessions152-loop173b.json").write_text(
        json.dumps(s152_new, indent=1), encoding="utf-8")
    s152_base = json.loads((ART173 / "sessions152-loop173.json").read_text(
        encoding="utf-8"))
    bmap = {(t["session"], t["n"]): t for t in s152_base}
    m152, nw152, ww152, rm152 = [], [], [], []
    for t in s152_new:
        b = bmap.get((t["session"], t["n"]))
        if b is None:
            m152.append({"turn": (t["session"], t["n"]),
                         "what": "missing-base"})
            continue
        if b["verdict"] != t["verdict"]:
            m152.append({"turn": (t["session"], t["n"]),
                         "base": b["verdict"], "new": t["verdict"]})
        if b["reply"] != t["reply"]:
            rm152.append({"turn": (t["session"], t["n"]),
                          "base": b["reply"][:80], "new": t["reply"][:80]})
        if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
            nw152.append((t["session"], t["n"]))
        if t["fact_writes"] != b["fact_writes"]:
            ww152.append({"turn": (t["session"], t["n"]),
                          "base": b["fact_writes"],
                          "new": t["fact_writes"]})
    print(f"sessions152: n={len(s152_new)} verdict_moves={len(m152)} "
          f"reply_moves={len(rm152)} new_wrong={nw152} "
          f"write_moves={ww152}", flush=True)
    summary["sessions152"] = {"n": len(s152_new), "verdict_moves": m152,
                              "reply_moves": rm152, "new_wrong": nw152,
                              "write_moves": ww152}
    summary["seconds"] = round(time.time() - t0, 1)
    (ART173B / "g3-173b-summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(f"G3 TOTAL seconds={summary['seconds']}")
    shutil.rmtree(work, ignore_errors=True)
    bad = (len(m136) + len(rm136) + len(nw136) + len(m143) + len(rm143)
           + len(nw143) + len(m152) + len(rm152) + len(nw152)
           + len(ww152))
    print(f"G3 verdict: {'PASS' if bad == 0 else 'FAIL'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
