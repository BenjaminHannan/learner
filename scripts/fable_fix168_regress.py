#!/usr/bin/env python3
"""Exp 168 G3 driver -- sessions152 + redteam136 + redteam143 through loop168.

Follows the scripts/fable_loop138b_sessions.py, fable_loop138b_junk.py and
fable_loop138b_redteam143.py patterns BY IMPORT (sealed cases + judges);
only the daemon under test is loop168, run loop168-only and compared
per-case against loop138b's own frozen results in
artifacts/fable-agent138b-20260922/ (sessions152-loop138b.json,
redteam143-loop138b.json, redteam136-loop138b.jsonl). Bar: 0 new WRONG /
0 new junk writes; every move predicted (J8 + K9 reply-only moves on
redteam143, verdicts identical). Outputs into
artifacts/fable-selfground168-20260922/regress168/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix168_regress.py
"""

from __future__ import annotations

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

import fable_fix129_common as C129  # noqa: E402 (mailbox driver, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop168_agent as L168  # noqa: E402 (agent under test)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)
import fable_session152_run as S152R  # noqa: E402 (sessions + judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-selfground168-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"

PREDICTED_REPLY_MOVES = {"J8", "K9", "O5"}  # -> "I have no opinions."


def new_daemon168(root: Path):
    cfg = copy.deepcopy(L168.DEFAULT_CONFIG168)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L168.Loop168Daemon(root, cfg=cfg, idle_seconds=3600.0)


def run_sessions(work: Path) -> dict:
    out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = work / "sessions" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        daemon = new_daemon168(root)
        turns = S152R.run_session(daemon, root, s)
        out[s["id"]] = [{**t, "verdict": j["verdict"], "why": j["why"]}
                        for t in turns
                        for j in [S152R.judge(t)]]
    (work / "sessions152-loop168.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def run_redteam143(work: Path) -> list[dict]:
    R143.Loop132Daemon = L168.Loop168Daemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L168.DEFAULT_CONFIG168)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = work / "scratch143"
    scratch.mkdir(parents=True, exist_ok=True)
    rows = [R143.run_case(c, scratch / c["id"], markers)
            for c in suite["cases"]]
    (work / "redteam143-loop168.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    return rows


def run_case136(row: dict, workroot: Path) -> dict:
    root = Path(tempfile.mkdtemp(prefix=row["id"] + "_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    t0 = time.time()
    try:
        daemon = new_daemon168(root)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"], "text": row["text"],
                "expect": row["expect"], "stored": [],
                "reply": f"BOOT-FAILED {type(exc).__name__}: {exc}",
                "verdict": "HARNESS-ERROR", "seconds": round(time.time()
                                                             - t0, 3)}
    (root / "inbox" / "msg_00.txt").write_text(row["text"], encoding="utf-8")
    log: list = []
    try:
        C129.process_pending(daemon, root, log)
        stored = [list(t) for t in L90.notebook_triples(daemon.loop.nb)]
        reply = log[-1]["reply"] if log else "NO-LOG"
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"], "text": row["text"],
                "expect": row["expect"], "stored": [],
                "reply": f"HARNESS-CAUGHT {type(exc).__name__}: {exc}",
                "verdict": "HARNESS-ERROR", "seconds": round(time.time()
                                                             - t0, 3)}
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
    return {"id": row["id"], "group": row["group"], "text": row["text"],
            "expect": exp, "stored": stored, "reply": reply,
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def run_redteam136(work: Path) -> list[dict]:
    cases = json.loads((ART136 / "cases136.json").read_text(encoding="utf-8"))
    tmp = work / "rt136-tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    rows = [run_case136(row, tmp) for row in cases]
    with (work / "redteam136-loop168.jsonl").open("w",
                                                  encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows


def main(argv=None) -> int:
    t0 = time.time()
    work = ART / "regress168"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    rc = 0
    rep: dict = {}

    # -- sessions152 --
    got = run_sessions(work)
    base = json.loads((ART138B / "sessions152-loop138b.json").read_text(
        encoding="utf-8"))
    smoves, new_wrong = [], 0
    c168: Counter = Counter()
    c138: Counter = Counter()
    for sid, turns in got.items():
        for t, b in zip(turns, base.get(sid, [])):
            c168[t["verdict"]] += 1
            c138[b["verdict"]] += 1
            if (t["verdict"] != b["verdict"]
                    or t.get("reply", "") != b.get("reply", "")):
                smoves.append({"session": sid, "n": t["n"],
                               "loop138b": b["verdict"], "loop168": t[
                                   "verdict"]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
    rep["sessions"] = {"loop138b": dict(c138), "loop168": dict(c168),
                       "moves": smoves, "new_wrong": new_wrong}
    print(f"sessions152 138b={dict(c138)} 168={dict(c168)} "
          f"moves={len(smoves)} new_wrong={new_wrong}", flush=True)
    if smoves or new_wrong:
        rc = 1

    # -- redteam143 --
    rows = run_redteam143(work)
    blob = json.loads((ART138B / "redteam143-loop138b.json").read_text(
        encoding="utf-8"))
    brows = blob["rows"] if isinstance(blob, dict) else blob
    b_by_id = {r["id"]: r for r in brows}
    tmoves, tnew = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        v_same = r["verdict"] == b["verdict"]
        r_same = r.get("reply", "") == b.get("reply", "")
        if not (v_same and r_same):
            tmoves.append({"id": r["id"], "loop138b": b["verdict"],
                           "loop168": r["verdict"],
                           "reply_moves": not r_same,
                           "predicted": (r["id"] in PREDICTED_REPLY_MOVES
                                         and v_same)})
            if r["verdict"] == "WRONG-ANSWER" and b[
                    "verdict"] != "WRONG-ANSWER":
                tnew += 1
    unpredicted = [m for m in tmoves if not m["predicted"]]
    rep["redteam143"] = {"moves": tmoves, "new_wrong": tnew,
                         "unpredicted": unpredicted}
    print(f"redteam143 moves={len(tmoves)} new_wrong={tnew} "
          f"unpredicted={len(unpredicted)}", flush=True)
    for m in tmoves:
        print(f"  MOVE {m['id']}: {m['loop138b']} -> {m['loop168']} "
              f"reply_moves={m['reply_moves']} predicted={m['predicted']}",
              flush=True)
    if unpredicted or tnew:
        rc = 1

    # -- redteam136 --
    rows136 = run_redteam136(work)
    b136 = {}
    with (ART138B / "redteam136-loop138b.json").open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                b136[r["id"]] = r
    jmoves, jnew = [], 0
    for r in rows136:
        b = b136.get(r["id"])
        if b is None:
            continue
        if (r["verdict"] != b["verdict"]
                or r.get("reply", "") != b.get("reply", "")):
            jmoves.append({"id": r["id"], "loop138b": b["verdict"],
                           "loop168": r["verdict"]})
            if r["verdict"] in ("WRONG-WRITE", "HARNESS-ERROR") and b[
                    "verdict"] not in ("WRONG-WRITE", "HARNESS-ERROR"):
                jnew += 1
    rep["redteam136"] = {"moves": jmoves, "new_bad": jnew,
                         "counts": dict(Counter(r["verdict"]
                                                for r in rows136))}
    print(f"redteam136 {rep['redteam136']['counts']} moves={len(jmoves)} "
          f"new_bad={jnew}", flush=True)
    if jmoves or jnew:
        rc = 1

    rep["seconds"] = round(time.time() - t0, 1)
    rep["pass"] = rc == 0
    (work / "regress168-summary.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"G3 {rep['seconds']}s -> {'PASS' if rc == 0 else 'FAIL'}",
          flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
