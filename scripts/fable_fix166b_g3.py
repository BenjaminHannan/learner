#!/usr/bin/env python3
"""Experiment 166b -- G3 sessions152 + redteam136/143 through loop166b (Muse).

Reuses sealed runners by import (read-only, never edited):
  sessions152: scripts/fable_session152_run.py run_session/judge +
    artifacts/fable-session152-20260922/sessions152.json
  redteam136: artifacts/fable-redteam136-20260922/cases136.json verdicts
    (fresh daemon dir per case, mailbox process_pending like the 136 runner)
  redteam143: scripts/fable_redteam143_run.py run_case + sealed cases/markers

loop166's side is FROZEN (artifacts/fable-me166-20260922/*-loop166.json,
read-only); only the loop166b arm runs live. Bar: 0 per-case verdict moves
vs loop166, 0 reply moves EXCEPT the 3 predicted S4 case-only returns,
0 new WRONG/WRONG-WRITE, 0 new writes. S4 turns 2/3/26 must be byte-identical
to loop162b's frozen rows (the 166 FAIL cascade is fixed); S4/1 keeps
loop166's predicted move vs 162b. redteam136 (145) + redteam143 (124):
zero moves.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix166b_g3.py
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
import fable_loop166b_agent as L166B  # noqa: E402 (this experiment)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)
import fable_session152_run as S152R  # noqa: E402 (runner fns, read-only)

ROOT = SCRIPTS.parent
ART166 = ROOT / "artifacts" / "fable-me166-20260922"
ART166B = ROOT / "artifacts" / "fable-me166b-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"

# Predicted moves (PASSMARKS.md, written before any registered run): exactly
# the 3 S4 reply-case returns below; S4/1 keeps loop166's state vs 162b.
PREDICTED_S152_RETURNS = {("S4-pets-identity", 2), ("S4-pets-identity", 3),
                          ("S4-pets-identity", 26)}
S4_N1_LOOP166 = ("OK", "Saved: your dog is biscuit.", 1)


def new_daemon(root: Path, idle: float = 3600.0):
    cfg = copy.deepcopy(L166B.DEFAULT_CONFIG166B)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L166B.Loop166bDaemon(root, cfg=cfg, idle_seconds=idle)


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
    base = copy.deepcopy(L166B.DEFAULT_CONFIG166B)
    R143.Loop132Daemon = L166B.Loop166bDaemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(base)  # type: ignore[method-assign]
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = workroot / "scratch143-loop166b"
    return [R143.run_case(c, scratch / c["id"], markers)
            for c in suite["cases"]]


def run_152(workroot: Path) -> list[dict]:
    sessions = json.loads((ART152 / "sessions152.json").read_text(
        encoding="utf-8"))
    turns_all = []
    for s in sessions:
        root = workroot / "s152-loop166b" / s["id"]
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
    ART166B.mkdir(parents=True, exist_ok=True)
    work = ART166B / "scratch-g3"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / "rt136").mkdir(parents=True)
    (work / "rt143").mkdir(parents=True)
    (work / "s152").mkdir(parents=True)
    t0 = time.time()
    summary: dict = {}

    f136 = json.loads((ART166 / "redteam136-loop166.json").read_text(
        encoding="utf-8"))
    r136 = run_136(work / "rt136")
    (ART166B / "redteam136-loop166b.json").write_text(
        json.dumps(r136, indent=1), encoding="utf-8")
    b136 = {r["id"]: r for r in f136}
    m136 = [r["id"] for r in r136
            if b136.get(r["id"], {}).get("verdict") != r["verdict"]
            or b136.get(r["id"], {}).get("reply") != r["reply"]]
    nw136 = [r["id"] for r in r136
             if r["verdict"] in ("WRONG-WRITE", "WRONG")
             and b136.get(r["id"], {}).get("verdict")
             not in ("WRONG-WRITE", "WRONG")]
    print(f"redteam136: n={len(r136)} moves={len(m136)} "
          f"new_wrong={nw136}", flush=True)
    summary["redteam136"] = {"n": len(r136), "moves": m136,
                             "new_wrong": nw136}

    f143 = json.loads((ART166 / "redteam143-loop166.json").read_text(
        encoding="utf-8"))
    r143 = run_143(work / "rt143")
    (ART166B / "redteam143-loop166b.json").write_text(
        json.dumps(r143, indent=1), encoding="utf-8")
    b143 = {r["id"]: r for r in f143}
    m143 = [r["id"] for r in r143
            if b143.get(r["id"], {}).get("verdict") != r["verdict"]
            or b143.get(r["id"], {}).get("reply") != r["reply"]]
    nw143 = [r["id"] for r in r143
             if r["verdict"] not in ("OK",)
             and b143.get(r["id"], {}).get("verdict") in ("OK",)]
    print(f"redteam143: n={len(r143)} moves={len(m143)} "
          f"new_bad={nw143}", flush=True)
    summary["redteam143"] = {"n": len(r143), "moves": m143,
                             "new_bad": nw143}

    f152 = json.loads((ART166 / "sessions152-loop166.json").read_text(
        encoding="utf-8"))
    f152b = json.loads((ART166 / "sessions152-loop162b.json").read_text(
        encoding="utf-8"))
    s152 = run_152(work / "s152")
    (ART166B / "sessions152-loop166b.json").write_text(
        json.dumps(s152, indent=1), encoding="utf-8")
    bmap = {(t["session"], t["n"]): t for t in f152}
    b162 = {(t["session"], t["n"]): t for t in f152b}
    m152, nw152, ww152, ret162 = [], [], [], []
    for t in s152:
        key = (t["session"], t["n"])
        b = bmap.get(key)
        if b is None:
            m152.append({"turn": key, "what": "missing-base"})
            continue
        if b["verdict"] != t["verdict"]:
            m152.append({"turn": key, "base": b["verdict"],
                         "new": t["verdict"]})
        if b["reply"] != t["reply"]:
            m152.append({"turn": key, "what": "reply-move",
                         "base": b["reply"][:80], "new": t["reply"][:80]})
        if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
            nw152.append(key)
        if t["fact_writes"] != b["fact_writes"]:
            ww152.append({"turn": key, "base": b["fact_writes"],
                          "new": t["fact_writes"]})
    print(f"sessions152: n={len(s152)} moves={len(m152)} "
          f"new_wrong={nw152} write_moves={ww152}", flush=True)
    # S4/1 keeps loop166's predicted state; the 3 returns match loop162b.
    n1 = [t for t in s152
          if (t["session"], t["n"]) == ("S4-pets-identity", 1)][0]
    n1_ok = (n1["verdict"] == S4_N1_LOOP166[0]
             and S4_N1_LOOP166[1] in n1["reply"]
             and n1["fact_writes"] == S4_N1_LOOP166[2])
    print(f"S4/1 keeps-166={n1_ok} ({n1['verdict']},{n1['fact_writes']})")
    for key in sorted(PREDICTED_S152_RETURNS):
        t = {(x["session"], x["n"]): x for x in s152}[key]
        b = b162[key]
        same = (t["verdict"] == b["verdict"] and t["reply"] == b["reply"]
                and t["fact_writes"] == b["fact_writes"])
        ret162.append({"turn": key, "identical_to_162b": same,
                       "new": t["reply"][:60], "base": b["reply"][:60]})
        print(f"  return {key}: identical_to_162b={same}")
    summary["sessions152"] = {"n": len(s152), "moves": m152,
                              "new_wrong": [list(k) for k in nw152],
                              "write_moves": ww152,
                              "s4n1_keeps_166": n1_ok,
                              "returns_vs_162b": ret162}
    summary["seconds"] = round(time.time() - t0, 1)
    (ART166B / "g3-166b-summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(f"G3 TOTAL seconds={summary['seconds']}")
    shutil.rmtree(work, ignore_errors=True)
    # ---- predicted-move triage (mechanical, from PASSMARKS.md) ----
    s152_set = set()
    for m in m152:
        t = m.get("turn")
        s152_set.add(tuple(t) if isinstance(t, list) else t)
    unpredicted = s152_set - PREDICTED_S152_RETURNS
    missing = PREDICTED_S152_RETURNS - s152_set
    print(f"s152 unpredicted={sorted(unpredicted, key=str)} "
          f"missing-predicted={sorted(missing, key=str)}")
    bad = (len(m136) + len(nw136) + len(m143) + len(nw143)
           + len(unpredicted) + len(missing) + len(nw152) + len(ww152)
           + (0 if n1_ok else 1)
           + sum(1 for r in ret162 if not r["identical_to_162b"]))
    print(f"G3 verdict: {'PASS' if bad == 0 else 'FAIL'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
