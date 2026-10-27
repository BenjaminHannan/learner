#!/usr/bin/env python3
"""Experiment 166 -- G3 sessions152 + redteam136/143 through loop166 (Muse).

Reuses sealed runners by import (read-only, never edited):
  sessions152: scripts/fable_session152_run.py run_session/judge +
    artifacts/fable-session152-20260922/sessions152.json
  redteam136: artifacts/fable-redteam136-20260922/cases136.json verdicts
    (fresh daemon dir per case, mailbox process_pending like the 136 runner)
  redteam143: scripts/fable_redteam143_run.py run_case + sealed cases/markers

Each suite runs through BOTH the base agent (loop162b) and loop166; the bar
is 0 per-case verdict moves, 0 new WRONG/WRONG-WRITE, 0 new junk writes.
(ZERO moves predicted in writing before the run: the me frames fire only on
first-person "my" possessives; the pre-seal scan finds no such teach/ask in
any G3 input, and no G3 reply can contain the raw USER key since none is
teachable there. The reply rewrite only fires on me-claimed turns.)

Note vs the brief: loop162b's own artifact folder holds no frozen
sessions/redteam rows, so the base side runs live in this script (162b
files are never edited, so its outputs are the frozen behaviour).

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix166_g3.py
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
import fable_loop162b_agent as L162B  # noqa: E402 (base agent, read-only)
import fable_loop166_agent as L166  # noqa: E402 (this experiment)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)
import fable_session152_run as S152R  # noqa: E402 (runner fns, read-only)

ROOT = SCRIPTS.parent
ART166 = ROOT / "artifacts" / "fable-me166-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"

# Predicted moves (PASSMARKS.md, written before any registered run): exactly
# one sessions152 turn changes by design -- (S4-pets-identity, n=1)
# "my dog is biscuit": base UNHELPFUL + clarify + 0 writes -> loop166 OK +
# "Saved: your dog is biscuit." + 1 write (USER, dog, biscuit). Case 143/136:
# zero moves (pre-seal scan: no first-person frame fires in any input).
PREDICTED_S152 = {("S4-pets-identity", 1)}

ARMS = {
    "loop162b": (L162B.Loop162bDaemon, copy.deepcopy(
        L162B.DEFAULT_CONFIG162B)),
    "loop166": (L166.Loop166Daemon, copy.deepcopy(
        L166.DEFAULT_CONFIG166)),
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
    ART166.mkdir(parents=True, exist_ok=True)
    work = ART166 / "scratch-g3"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / "rt136").mkdir(parents=True)
    (work / "rt143").mkdir(parents=True)
    (work / "s152").mkdir(parents=True)
    t0 = time.time()
    summary: dict = {}
    r136 = {t: run_136(t, work / "rt136") for t in ("loop162b", "loop166")}
    (ART166 / "redteam136-loop162b.json").write_text(
        json.dumps(r136["loop162b"], indent=1), encoding="utf-8")
    (ART166 / "redteam136-loop166.json").write_text(
        json.dumps(r136["loop166"], indent=1), encoding="utf-8")
    m136 = diff_rows(r136["loop162b"], r136["loop166"])
    nw136 = [r["id"] for r in r136["loop166"]
             if r["verdict"] in ("WRONG-WRITE", "WRONG")
             and {x["id"]: x for x in r136["loop162b"]}[r["id"]]["verdict"]
             not in ("WRONG-WRITE", "WRONG")]
    print(f"redteam136: n={len(r136['loop166'])} moves={len(m136)} "
          f"new_wrong={nw136}", flush=True)
    summary["redteam136"] = {"n": len(r136["loop166"]), "moves": m136,
                             "new_wrong": nw136}

    r143 = {t: run_143(t, work / "rt143") for t in ("loop162b", "loop166")}
    (ART166 / "redteam143-loop162b.json").write_text(
        json.dumps(r143["loop162b"], indent=1), encoding="utf-8")
    (ART166 / "redteam143-loop166.json").write_text(
        json.dumps(r143["loop166"], indent=1), encoding="utf-8")
    m143 = diff_rows(r143["loop162b"], r143["loop166"])
    nw143 = [r["id"] for r in r143["loop166"]
             if r["verdict"] not in ("OK",)
             and {x["id"]: x for x in r143["loop162b"]}[r["id"]]["verdict"]
             in ("OK",)]
    print(f"redteam143: n={len(r143['loop166'])} moves={len(m143)} "
          f"new_bad={nw143}", flush=True)
    summary["redteam143"] = {"n": len(r143["loop166"]), "moves": m143,
                             "new_bad": nw143}

    s152 = {t: run_152(t, work / "s152") for t in ("loop162b", "loop166")}
    (ART166 / "sessions152-loop162b.json").write_text(
        json.dumps(s152["loop162b"], indent=1), encoding="utf-8")
    (ART166 / "sessions152-loop166.json").write_text(
        json.dumps(s152["loop166"], indent=1), encoding="utf-8")
    bmap = {(t["session"], t["n"]): t for t in s152["loop162b"]}
    m152, nw152, ww152 = [], [], []
    for t in s152["loop166"]:
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
    print(f"sessions152: n={len(s152['loop166'])} moves={len(m152)} "
          f"new_wrong={nw152} write_moves={ww152}", flush=True)
    summary["sessions152"] = {"n": len(s152["loop166"]), "moves": m152,
                              "new_wrong": nw152, "write_moves": ww152}
    summary["seconds"] = round(time.time() - t0, 1)
    (ART166 / "g3-166-summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(f"G3 TOTAL seconds={summary['seconds']}")
    shutil.rmtree(work, ignore_errors=True)
    # ---- predicted-move triage (mechanical, from PASSMARKS.md) ----
    s152_set = set()
    for m in m152:
        t = m.get("turn")
        s152_set.add(tuple(t) if isinstance(t, list) else t)
    unpredicted = (s152_set - PREDICTED_S152)
    missing = (PREDICTED_S152 - s152_set)
    pred_ok = True
    if not missing:
        t = [x for x in s152["loop166"]
             if (x["session"], x["n"]) == ("S4-pets-identity", 1)][0]
        b = {(x["session"], x["n"]): x for x in s152["loop162b"]}[
            ("S4-pets-identity", 1)]
        pred_ok = (t["verdict"] == "OK" and b["verdict"] == "UNHELPFUL"
                   and "Saved: your dog is biscuit." in t["reply"]
                   and t["fact_writes"] == 1 and b["fact_writes"] == 0)
        print(f"S4-pets-identity/1 as-predicted={pred_ok} "
              f"base=({b['verdict']},{b['fact_writes']}) "
              f"new=({t['verdict']},{t['fact_writes']})")
    print(f"s152 unpredicted={sorted(unpredicted, key=str)} "
          f"missing-predicted={sorted(missing, key=str)}")
    # ww152 counts the predicted turn's write move; subtract it back.
    # nw152 is unaffected (predicted verdict is OK, not WRONG).
    ww_pred = [w for w in ww152
               if tuple(w["turn"]) in PREDICTED_S152]
    bad = (len(m136) + len(nw136) + len(m143) + len(nw143)
           + len(unpredicted) + len(missing) + len(nw152)
           + len([w for w in ww152 if tuple(w["turn"])
                   not in PREDICTED_S152])
           + (0 if (pred_ok and not missing) else 1))
    print(f"G3 verdict: {'PASS' if bad == 0 else 'FAIL'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
