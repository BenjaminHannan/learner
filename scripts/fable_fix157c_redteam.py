#!/usr/bin/env python3
"""Experiment 157c -- G3 redteam136 + redteam143 through loop157c AND loop157b.

Two arms run FRESH in the same driver (mailbox, fresh dir per case) and
are diffed per-case; judges mirror the sealed runners by import:

  redteam136: cases from artifacts/fable-redteam136-20260922/cases136.json
    (145 cases), mailbox via fable_fix129_common.process_pending, verdict
    rule copied from scripts/fable_fix139b_redteam136.py run_case139b
    (nowrite -> OK iff no stored triple; else stored==want -> OK,
    none -> MISSED, else WRONG-WRITE).
  redteam143: cases from
    artifacts/fable-redteam143-20260922/fable_redteam143_cases.json,
    mailbox process_file per turn, judge helpers (norm, extract_answer,
    teach_accepted, markers) imported from scripts/fable_redteam143_run.py.

Predicted moves: none (pre-seal scans: 0 157b-strip fires on rt136
texts; 0 on rt143 teaches+questions). Bar: 0 new WRONG/WRONG-WRITE and
0 new junk writes on the new arm, every move predicted in PASSMARKS.md.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix157c_redteam.py
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
import fable_loop157b_agent as L157B  # noqa: E402 (base arm, read-only)
import fable_loop157c_agent as L157C  # noqa: E402 (this experiment)
import fable_redteam143_run as R143  # noqa: E402 (judge helpers, read-only)

ROOT = SCRIPTS.parent
ART157C = ROOT / "artifacts" / "fable-title157c-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
ART143 = ROOT / "artifacts" / "fable-redteam143-20260922"


def new_daemon157c(root: Path):
    cfg = copy.deepcopy(L157C.DEFAULT_CONFIG157C)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L157C.Loop157cDaemon(root, cfg=cfg, idle_seconds=3600.0)


def new_daemon157b(root: Path):
    cfg = copy.deepcopy(L157B.DEFAULT_CONFIG157B)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L157B.Loop157bDaemon(root, cfg=cfg, idle_seconds=3600.0)


def run_case136(row: dict, workroot: Path, factory, tag: str) -> dict:
    root = Path(tempfile.mkdtemp(prefix=row["id"] + f"_{tag}_",
                                 dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    t0 = time.time()
    try:
        daemon = factory(root)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"], "text": row["text"],
                "expect": row["expect"], "stored": [],
                "reply": f"BOOT-FAILED {type(exc).__name__}: {exc}",
                "verdict": "HARNESS-ERROR", "seconds": round(time.time() - t0, 3)}
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
                "verdict": "HARNESS-ERROR", "seconds": round(time.time() - t0, 3)}
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


def run_case143(case: dict, workdir: Path, daemon_cls, cfg: dict,
                markers: list[str]) -> dict:
    rec = {"id": case["id"], "family": case.get("family", ""),
           "expected": case["expected"], "verdict": "OK",
           "teach_replies": [], "reply": "", "extracted": "",
           "reasons": []}
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        daemon = daemon_cls(str(workdir), cfg=dict(cfg))
    except Exception as exc:  # noqa: BLE001
        rec["verdict"] = "HARNESS-ERROR"
        rec["reasons"].append(f"boot failed: {exc!r}")
        return rec
    try:
        for i, text in enumerate(list(case["teaches"]) + [case["question"]]):
            fname = f"t{i:02d}.txt"
            (workdir / "inbox" / fname).write_text(str(text) + "\n",
                                                  encoding="utf-8")
            daemon.process_file(workdir / "inbox" / fname)
            reply = (workdir / "outbox" / fname).read_text(
                encoding="utf-8").strip()
            if i < len(case["teaches"]):
                rec["teach_replies"].append(reply)
                if not R143.teach_accepted(reply):
                    rec["verdict"] = "HARNESS-ERROR"
                    rec["reasons"].append(f"teach {i} rejected: {reply!r}")
                    rec["reply"] = reply
                    return rec
            else:
                rec["reply"] = reply
    except Exception as exc:  # noqa: BLE001
        rec["verdict"] = "HARNESS-ERROR"
        rec["reasons"].append(f"turn raised {exc!r}")
        return rec
    reply = rec["reply"]
    low = reply.lower()
    abst = any(m.lower() in low for m in markers)
    exp = case["expected"]
    rec["extracted"] = R143.extract_answer(reply)
    if exp == "abstain":
        if not abst:
            rec["verdict"] = "WRONG-ANSWER"
            rec["reasons"].append(
                f"confident reply where abstain sealed: {reply!r}")
    else:
        if R143.norm(rec["extracted"]) == R143.norm(exp) and R143.norm(exp):
            pass
        elif abst:
            rec["verdict"] = "MISSED"
            rec["reasons"].append(
                f"abstained though answer sealed ({exp!r}): {reply!r}")
        else:
            rec["verdict"] = "WRONG-ANSWER"
            rec["reasons"].append(
                f"confident {rec['extracted']!r} != sealed {exp!r}: {reply!r}")
    return rec


def main() -> int:
    t0 = time.time()
    ART157C.mkdir(parents=True, exist_ok=True)
    # ---- redteam136, both arms ----
    cases136 = json.loads((ART136 / "cases136.json").read_text(encoding="utf-8"))
    if isinstance(cases136, dict):
        cases136 = cases136.get("cases", [])
    workroot = ART157C / "work-rt136"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    rows_c = [run_case136(r, workroot, new_daemon157c, "c") for r in cases136]
    rows_b = [run_case136(r, workroot, new_daemon157b, "b") for r in cases136]
    (ART157C / "redteam136-loop157c.json").write_text(
        json.dumps(rows_c, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (ART157C / "redteam136-loop157b.json").write_text(
        json.dumps(rows_b, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    b136 = {r["id"]: r for r in rows_b}
    moves136 = [r["id"] for r in rows_c
                if (b136.get(r["id"], {}).get("verdict"), b136.get(r["id"], {}).get("reply"))
                != (r["verdict"], r["reply"])]
    new_wrong136 = [r["id"] for r in rows_c
                    if r["verdict"] == "WRONG-WRITE"
                    and b136.get(r["id"], {}).get("verdict") != "WRONG-WRITE"]
    new_writes136 = [r["id"] for r in rows_c
                     if r["stored"] and not b136.get(r["id"], {}).get("stored")]
    cc: dict[str, int] = {}
    for r in rows_c:
        cc[r["verdict"]] = cc.get(r["verdict"], 0) + 1
    print(f"rt136 n={len(rows_c)} counts={cc} moves={moves136} "
          f"new_wrong={new_wrong136} new_writes={new_writes136}", flush=True)
    shutil.rmtree(workroot, ignore_errors=True)
    # ---- redteam143, both arms ----
    spec = json.loads((ART143 / "fable_redteam143_cases.json").read_text(encoding="utf-8"))
    cases143 = spec.get("cases", spec) if isinstance(spec, dict) else spec
    markers = list(spec.get("abstain_markers", [])) if isinstance(spec, dict) else []
    work143 = ART157C / "work-rt143"
    if work143.exists():
        shutil.rmtree(work143)
    work143.mkdir(parents=True)
    cfg_c = copy.deepcopy(L157C.DEFAULT_CONFIG157C)
    cfg_b = copy.deepcopy(L157B.DEFAULT_CONFIG157B)
    out_c = [run_case143(c, work143 / f"c_{c['id']}", L157C.Loop157cDaemon, cfg_c, markers)
             for c in cases143]
    out_b = [run_case143(c, work143 / f"b_{c['id']}", L157B.Loop157bDaemon, cfg_b, markers)
             for c in cases143]
    (ART157C / "redteam143-loop157c.json").write_text(
        json.dumps(out_c, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (ART157C / "redteam143-loop157b.json").write_text(
        json.dumps(out_b, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    b143 = {r["id"]: r for r in out_b}
    moves143 = [r["id"] for r in out_c
                if (b143.get(r["id"], {}).get("verdict"), b143.get(r["id"], {}).get("reply"))
                != (r["verdict"], r["reply"])]
    new_wrong143 = [r["id"] for r in out_c
                    if r["verdict"] == "WRONG-ANSWER"
                    and b143.get(r["id"], {}).get("verdict") != "WRONG-ANSWER"]
    cb: dict[str, int] = {}
    for r in out_c:
        cb[r["verdict"]] = cb.get(r["verdict"], 0) + 1
    print(f"rt143 n={len(out_c)} counts={cb} moves={moves143} "
          f"new_wrong={new_wrong143}", flush=True)
    shutil.rmtree(work143, ignore_errors=True)
    total = round(time.time() - t0, 1)
    (ART157C / "redteam157c-summary.json").write_text(json.dumps(
        {"rt136": {"counts": cc, "moves": moves136, "new_wrong": new_wrong136,
                   "new_writes": new_writes136},
         "rt143": {"counts": cb, "moves": moves143, "new_wrong": new_wrong143},
         "seconds": total}, indent=1), encoding="utf-8")
    print(f"TOTAL {total} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
