#!/usr/bin/env python3
"""Experiment 192 -- C3 sessions152 + redteam136/143 through loop192.

Reuses sealed runners by import (read-only, never edited), same pattern
as scripts/fable_fix167e_g3.py:
  sessions152: scripts/fable_session152_run.py run_session/judge +
    artifacts/fable-session152-20260922/sessions152.json
  redteam136: artifacts/fable-redteam136-20260922/cases136.json verdicts
    (fresh daemon dir per case, mailbox process_pending like the 136 runner)
  redteam143: scripts/fable_redteam143_run.py run_case + sealed cases/markers

Each suite runs through loop192 ONLY; the bar is set against loop167e's
FROZEN rows (artifacts/fable-label167e-20260922/redteam136-loop167e.json,
redteam143-loop167e.json, sessions152-loop167e.json, read-only): 0
per-case verdict moves, 0 new WRONG/WRONG-WRITE, 0 write-count moves
(stored/fact_writes identical), and reply moves ONLY by the shared
correct-reply rule (fable_fix192_correctreply.correctreply_move:
byte-identical, or a Saved confirmation moved to the sealed Updated
template with the same subject, relation surface, and new value).

Predicted moves: see PASSMARKS.md (written before the run; pre-seal dev
scan of the frozen loop167e rows over these suites). Any other move
fails C3 honestly. Outputs go into
artifacts/fable-correctreply192-20260922/ only.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix192_suites.py
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
import fable_fix192_correctreply as F192  # noqa: E402 (shared move rule)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop192_agent as L192  # noqa: E402 (this experiment)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)
import fable_session152_run as S152R  # noqa: E402 (runner fns, read-only)

ROOT = SCRIPTS.parent
ART167E = ROOT / "artifacts" / "fable-label167e-20260922"
ART192 = ROOT / "artifacts" / "fable-correctreply192-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"


def new_daemon(root: Path, idle: float = 3600.0):
    cfg = copy.deepcopy(L192.DEFAULT_CONFIG192)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L192.Loop192Daemon(root, cfg=cfg, idle_seconds=idle)


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
    cls = L192.Loop192Daemon
    base = copy.deepcopy(L192.DEFAULT_CONFIG192)
    R143.Loop132Daemon = cls  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(base)  # type: ignore[method-assign]
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = workroot / "scratch143-loop192"
    return [R143.run_case(c, scratch / c["id"], markers)
            for c in suite["cases"]]


def run_152(workroot: Path) -> list[dict]:
    sessions = json.loads((ART152 / "sessions152.json").read_text(
        encoding="utf-8"))
    turns_all = []
    for s in sessions:
        root = workroot / "s152-loop192" / s["id"]
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


def check_reply_rows(new, frozen, key="id"):
    """Verdict+stored identical; reply identical-or-correctreply-move."""
    b = {r[key]: r for r in frozen}
    verdict_moves, stored_moves, reply_moves, reply_bad = [], [], [], []
    for r in new:
        br = b.get(r[key])
        if br is None:
            verdict_moves.append({"id": r[key], "what": "missing-base"})
            continue
        if br.get("verdict") != r.get("verdict"):
            verdict_moves.append({"id": r[key], "base": br.get("verdict"),
                                  "new": r.get("verdict")})
        if br.get("stored") != r.get("stored"):
            stored_moves.append(r[key])
        if not F192.correctreply_move(br.get("reply", ""),
                                      r.get("reply", "")):
            reply_bad.append(r[key])
        elif br.get("reply") != r.get("reply"):
            reply_moves.append(r[key])
    return verdict_moves, stored_moves, reply_moves, reply_bad


def main() -> int:
    ART192.mkdir(parents=True, exist_ok=True)
    work = ART192 / "scratch-suites"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / "rt136").mkdir(parents=True)
    (work / "rt143").mkdir(parents=True)
    (work / "s152").mkdir(parents=True)
    t0 = time.time()
    summary: dict = {}
    ok_all = True

    r136 = run_136(work / "rt136")
    (ART192 / "redteam136-loop192.json").write_text(
        json.dumps(r136, indent=1), encoding="utf-8")
    frozen136 = json.loads((ART167E / "redteam136-loop167e.json").read_text(
        encoding="utf-8"))
    v136, s136, rm136, rb136 = check_reply_rows(r136, frozen136)
    nw136 = [r["id"] for r in r136
             if r["verdict"] in ("WRONG-WRITE", "WRONG")
             and {x["id"]: x for x in frozen136}[r["id"]]["verdict"]
             not in ("WRONG-WRITE", "WRONG")]
    print(f"redteam136: n={len(r136)} verdict_moves={len(v136)} "
          f"stored_moves={len(s136)} reply_moves={rm136} "
          f"reply_bad={rb136} new_wrong={nw136}", flush=True)
    summary["redteam136"] = {"n": len(r136), "verdict_moves": v136,
                             "stored_moves": s136, "reply_moves": rm136,
                             "reply_bad": rb136, "new_wrong": nw136}
    ok_all = ok_all and not (v136 or s136 or rb136 or nw136)

    r143 = run_143(work / "rt143")
    (ART192 / "redteam143-loop192.json").write_text(
        json.dumps(r143, indent=1), encoding="utf-8")
    frozen143 = json.loads((ART167E / "redteam143-loop167e.json").read_text(
        encoding="utf-8"))
    v143, s143, rm143, rb143 = check_reply_rows(r143, frozen143)
    nw143 = [r["id"] for r in r143
             if r["verdict"] not in ("OK",)
             and {x["id"]: x for x in frozen143}[r["id"]]["verdict"]
             in ("OK",)]
    print(f"redteam143: n={len(r143)} verdict_moves={len(v143)} "
          f"stored_moves={len(s143)} reply_moves={rm143} "
          f"reply_bad={rb143} new_bad={nw143}", flush=True)
    summary["redteam143"] = {"n": len(r143), "verdict_moves": v143,
                             "stored_moves": s143, "reply_moves": rm143,
                             "reply_bad": rb143, "new_bad": nw143}
    ok_all = ok_all and not (v143 or s143 or rb143 or nw143)

    s152 = run_152(work / "s152")
    (ART192 / "sessions152-loop192.json").write_text(
        json.dumps(s152, indent=1), encoding="utf-8")
    frozen152 = json.loads((ART167E / "sessions152-loop167e.json").read_text(
        encoding="utf-8"))
    bmap = {(t["session"], t["n"]): t for t in frozen152}
    m152, nw152, ww152, rm152, rb152 = [], [], [], [], []
    for t in s152:
        k = (t["session"], t["n"])
        b = bmap.get(k)
        if b is None:
            m152.append({"turn": k, "what": "missing-base"})
            continue
        if b["verdict"] != t["verdict"]:
            m152.append({"turn": k, "base": b["verdict"],
                         "new": t["verdict"]})
        if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
            nw152.append(k)
        if t.get("fact_writes") != b.get("fact_writes"):
            ww152.append({"turn": k, "base": b.get("fact_writes"),
                          "new": t.get("fact_writes")})
        if not F192.correctreply_move(b.get("reply", ""),
                                      t.get("reply", "")):
            rb152.append(k)
        elif b.get("reply") != t.get("reply"):
            rm152.append(k)
    print(f"sessions152: n={len(s152)} verdict_moves={len(m152)} "
          f"new_wrong={nw152} write_moves={len(ww152)} "
          f"reply_moves={rm152} reply_bad={rb152}", flush=True)
    summary["sessions152"] = {"n": len(s152), "verdict_moves": m152,
                              "new_wrong": nw152, "write_moves": ww152,
                              "reply_moves": rm152, "reply_bad": rb152}
    ok_all = ok_all and not (m152 or nw152 or ww152 or rb152)

    summary["seconds"] = round(time.time() - t0, 1)
    (ART192 / "suites192-summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(f"SUITES TOTAL seconds={summary['seconds']} "
          f"SUITES {'PASS' if ok_all else 'FAIL'}")
    shutil.rmtree(work, ignore_errors=True)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
