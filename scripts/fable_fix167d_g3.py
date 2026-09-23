#!/usr/bin/env python3
"""Experiment 167d -- G3 sessions152 + redteam136/143 through loop167d (Muse).

Reuses sealed runners by import (read-only, never edited), same pattern as
scripts/fable_fix167b_g3.py:
  sessions152: scripts/fable_session152_run.py run_session/judge +
    artifacts/fable-session152-20260922/sessions152.json
  redteam136: artifacts/fable-redteam136-20260922/cases136.json verdicts
    (fresh daemon dir per case, mailbox process_pending like the 136 runner)
  redteam143: scripts/fable_redteam143_run.py run_case + sealed cases/markers

Each suite runs through BOTH the base agent (loop167b) and loop167d; the
bar is 0 per-case verdict moves, 0 new WRONG/WRONG-WRITE, 0 new writes
(ZERO moves predicted in writing before the run: the added 167d shapes
are disjoint from every 167b-claimed shape, and the pre-seal
exact-schema scan found no added-frame hit in any G3 input -- cases136,
rt143 cases, sessions152 turns -- so no G3 turn can reach the added
stage). The new arm is additionally diffed against loop167b's frozen G3
rows (artifacts/fable-verb167b-20260922/redteam136-loop167b.json,
redteam143-loop167b.json, sessions152-loop167b.json, read-only).

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix167d_g3.py
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
import fable_loop167b_agent as L167B  # noqa: E402 (base agent, read-only)
import fable_loop167d_agent as L167D  # noqa: E402 (this experiment)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)
import fable_session152_run as S152R  # noqa: E402 (runner fns, read-only)

ROOT = SCRIPTS.parent
ART167B = ROOT / "artifacts" / "fable-verb167b-20260922"
ART167D = ROOT / "artifacts" / "fable-verb167d-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"

ARMS = {
    "loop167b": (L167B.Loop167bDaemon, copy.deepcopy(
        L167B.DEFAULT_CONFIG167B)),
    "loop167d": (L167D.Loop167dDaemon, copy.deepcopy(
        L167D.DEFAULT_CONFIG167D)),
}


def new_daemon(tag: str, root: Path, idle: float = 3600.0):
    cls, base = ARMS[tag]
    cfg = copy.deepcopy(base)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return cls(root, cfg=cfg, idle_seconds=idle)


def run_136(tag: str, workroot: Path) -> list[dict]:
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    rows = []
    for row in cases:
        root = Path(tempfile.mkdtemp(prefix=row["id"] + "_",
                                     dir=str(workroot)))
        (root / "inbox").mkdir(exist_ok=True)
        t0 = time.time()
        try:
            daemon = new_daemon(tag, root)
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


def run_143(tag: str, workroot: Path) -> list[dict]:
    cls, base = ARMS[tag]
    R143.Loop132Daemon = cls  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(base)  # type: ignore[method-assign]
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = workroot / f"scratch143-{tag}"
    return [R143.run_case(c, scratch / c["id"], markers)
            for c in suite["cases"]]


def run_152(tag: str, workroot: Path) -> list[dict]:
    sessions = json.loads((ART152 / "sessions152.json").read_text(
        encoding="utf-8"))
    turns_all = []
    for s in sessions:
        root = workroot / f"s152-{tag}" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        daemon = new_daemon(tag, root)
        turns = S152R.run_session(daemon, root, s)
        for t in turns:
            t.update(S152R.judge(t))
            t["session"] = s["id"]
        turns_all.extend(turns)
    return turns_all


def diff_rows(base, new, key="id", fields=("verdict",)):
    b = {r[key]: r for r in base}
    moves = []
    for r in new:
        br = b.get(r[key])
        if br is None:
            moves.append({"id": r[key], "what": "missing-base"})
            continue
        for f in fields:
            if br.get(f) != r.get(f):
                moves.append({"id": r[key], "field": f,
                              "base": br.get(f), "new": r.get(f)})
    return moves


def main() -> int:
    ART167D.mkdir(parents=True, exist_ok=True)
    work = ART167D / "scratch-g3"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / "rt136").mkdir(parents=True)
    (work / "rt143").mkdir(parents=True)
    (work / "s152").mkdir(parents=True)
    t0 = time.time()
    summary: dict = {}
    r136 = {t: run_136(t, work / "rt136") for t in ("loop167b", "loop167d")}
    (ART167D / "redteam136-loop167b.json").write_text(
        json.dumps(r136["loop167b"], indent=1), encoding="utf-8")
    (ART167D / "redteam136-loop167d.json").write_text(
        json.dumps(r136["loop167d"], indent=1), encoding="utf-8")
    m136 = diff_rows(r136["loop167b"], r136["loop167d"])
    nw136 = [r["id"] for r in r136["loop167d"]
             if r["verdict"] in ("WRONG-WRITE", "WRONG")
             and {x["id"]: x for x in r136["loop167b"]}[r["id"]]["verdict"]
             not in ("WRONG-WRITE", "WRONG")]
    frozen136 = json.loads((ART167B / "redteam136-loop167b.json").read_text(
        encoding="utf-8"))
    m136_167b = diff_rows(frozen136, r136["loop167d"])
    print(f"redteam136: n={len(r136['loop167d'])} moves_vs167b={len(m136)} "
          f"new_wrong={nw136} moves_vsfrozen={len(m136_167b)}", flush=True)
    summary["redteam136"] = {"n": len(r136["loop167d"]), "moves": m136,
                             "new_wrong": nw136,
                             "moves_vs_frozen167b": m136_167b}

    r143 = {t: run_143(t, work / "rt143") for t in ("loop167b", "loop167d")}
    (ART167D / "redteam143-loop167b.json").write_text(
        json.dumps(r143["loop167b"], indent=1), encoding="utf-8")
    (ART167D / "redteam143-loop167d.json").write_text(
        json.dumps(r143["loop167d"], indent=1), encoding="utf-8")
    m143 = diff_rows(r143["loop167b"], r143["loop167d"])
    nw143 = [r["id"] for r in r143["loop167d"]
             if r["verdict"] not in ("OK",)
             and {x["id"]: x for x in r143["loop167b"]}[r["id"]]["verdict"]
             in ("OK",)]
    frozen143 = json.loads((ART167B / "redteam143-loop167b.json").read_text(
        encoding="utf-8"))
    m143_167b = diff_rows(frozen143, r143["loop167d"])
    print(f"redteam143: n={len(r143['loop167d'])} moves_vs167b={len(m143)} "
          f"new_bad={nw143} moves_vsfrozen={len(m143_167b)}", flush=True)
    summary["redteam143"] = {"n": len(r143["loop167d"]), "moves": m143,
                             "new_bad": nw143,
                             "moves_vs_frozen167b": m143_167b}

    s152 = {t: run_152(t, work / "s152") for t in ("loop167b", "loop167d")}
    (ART167D / "sessions152-loop167b.json").write_text(
        json.dumps(s152["loop167b"], indent=1), encoding="utf-8")
    (ART167D / "sessions152-loop167d.json").write_text(
        json.dumps(s152["loop167d"], indent=1), encoding="utf-8")
    bmap = {(t["session"], t["n"]): t for t in s152["loop167b"]}
    m152, nw152, ww152 = [], [], []
    for t in s152["loop167d"]:
        b = bmap.get((t["session"], t["n"]))
        if b is None:
            m152.append({"turn": (t["session"], t["n"]),
                         "what": "missing-base"})
            continue
        if b["verdict"] != t["verdict"]:
            m152.append({"turn": (t["session"], t["n"]),
                         "base": b["verdict"], "new": t["verdict"]})
        if b["reply"] != t["reply"]:
            m152.append({"turn": (t["session"], t["n"]), "what": "reply-move",
                         "base": b["reply"][:80], "new": t["reply"][:80]})
        if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
            nw152.append((t["session"], t["n"]))
        if t["fact_writes"] != b["fact_writes"]:
            ww152.append({"turn": (t["session"], t["n"]),
                          "base": b["fact_writes"],
                          "new": t["fact_writes"]})
    frozen152 = json.loads((ART167B / "sessions152-loop167b.json").read_text(
        encoding="utf-8"))
    fmap = {(t["session"], t["n"]): t for t in frozen152}
    mmap = {(t["session"], t["n"]): t for t in s152["loop167d"]}
    m152_167b = [k for k in mmap if fmap.get(k, {}).get("reply")
                 != mmap[k]["reply"]]
    print(f"sessions152: n={len(s152['loop167d'])} moves={len(m152)} "
          f"new_wrong={nw152} write_moves={ww152} "
          f"reply_moves_vsfrozen={len(m152_167b)}", flush=True)
    summary["sessions152"] = {"n": len(s152["loop167d"]), "moves": m152,
                              "new_wrong": nw152, "write_moves": ww152,
                              "reply_moves_vs_frozen167b": m152_167b}
    summary["seconds"] = round(time.time() - t0, 1)
    (ART167D / "g3-167d-summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(f"G3 TOTAL seconds={summary['seconds']}")
    shutil.rmtree(work, ignore_errors=True)
    bad = (len(m136) + len(nw136) + len(m143) + len(nw143) + len(m152)
           + len(nw152) + len(ww152) + len(m136_167b) + len(m143_167b)
           + len(m152_167b))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
