#!/usr/bin/env python3
"""Experiment 154d frozen-suite driver -- loop138f suites re-run on loop154d.

Reuses the sealed 138f case runners read-only (same cases, same judges);
only the agent under test is loop154d (Loop154dDaemon / build_agent154d).
Every suite compares per-case against the SEALED loop138f rows (bar:
identical except the PASSMARKS-predicted yes/no moves) and counts new
WRONG / WRONG-WRITE / junk writes vs the sealed loop138b rows. Outputs go
to --art (default artifacts/fable-yesno154d-20260922/).

Suites: redteam136, cases150, f1, cases139b (M4 seven-case check),
redteam143 (M3 check), sessions152, bench (G1, all four splits).

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix154d_suites.py --suite all

Run one suite at a time under parallel-agent load:
  ... python -B scripts/fable_fix154d_suites.py --suite redteam143
"""

from __future__ import annotations

import argparse
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

import fable_bench121_run as B  # noqa: E402 (run_item/scorer, read-only)
import fable_fix129_punct as _P129  # noqa: E402 (import order only)
import fable_fix139b_probe as P139b  # noqa: E402 (judge, read-only)
import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
import fable_fix150_probe as P150  # noqa: E402 (judge, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop154d_agent as L154d  # noqa: E402 (agent under test)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)
import fable_session152_run as S152R  # noqa: E402 (sessions + judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-yesno154d-20260922"
ART138F = ROOT / "artifacts" / "fable-agent138f-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
ART139B = ROOT / "artifacts" / "fable-fix139b-20260922"
ART144 = ROOT / "artifacts" / "fable-fix144-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"

SEVEN = {"redteam136": ["C124", "C127", "C129", "C142"],
         "cases139b": ["C10", "C21"]}


def build154d(extra: dict) -> object:
    cfg = copy.deepcopy(L154d.DEFAULT_CONFIG154D)
    cfg.update(extra)
    return L154d.build_agent154d(cfg)


def new_daemon154d(root: Path):
    cfg = copy.deepcopy(L154d.DEFAULT_CONFIG154D)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L154d.Loop154dDaemon(root, cfg=cfg, idle_seconds=3600.0)


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                         sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def rows138f(name: str) -> list[dict]:
    return [json.loads(l) for l in
            (ART138F / name).read_text(encoding="utf-8").splitlines()
            if l.strip()]


def base_rows(name: str) -> list[dict]:
    return [json.loads(l) for l in
            (ART138B / name).read_text(encoding="utf-8").splitlines()
            if l.strip()]


def run_redteam136(art: Path) -> dict:
    R136.new_daemon139b = new_daemon154d  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = art / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows(art / "redteam136-loop154d.json", rows)
    f_by_id = {r["id"]: r for r in rows138f("redteam136-loop138f.json")}
    b_by_id = {r["id"]: r for r in base_rows("redteam136-loop138b.json")}
    moves, moves138f, new_wrong = [], [], 0
    for r in rows:
        f = f_by_id.get(r["id"])
        if f is not None and (r["verdict"] != f["verdict"] or
                              str(r.get("reply", "")).strip() !=
                              str(f.get("reply", "")).strip()):
            moves138f.append({"id": r["id"], "loop138f": f["verdict"],
                              "loop154d": r["verdict"]})
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "loop138b": b["verdict"],
                          "loop154d": r["verdict"]})
            if r["verdict"] == "WRONG-WRITE" and \
                    b["verdict"] != "WRONG-WRITE":
                new_wrong += 1
    seven = {}
    for cid in SEVEN["redteam136"]:
        r = {x["id"]: x for x in rows}.get(cid, {})
        b = b_by_id.get(cid, {})
        seven[cid] = (r.get("verdict") == b.get("verdict")
                      and str(r.get("reply", "")).strip()
                      == str(b.get("reply", "")).strip()
                      and r.get("stored", "n/a") == b.get("stored", "n/a"))
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_138b": new_wrong, "moves_vs_138b": moves,
            "moves_vs_138f": moves138f, "seven138b": seven}


def run_cases150(art: Path) -> dict:
    cases = json.loads((ART150 / "cases150.json").read_text(encoding="utf-8"))
    rows = [P150.run_case(row, build154d) for row in cases]
    write_rows(art / "probe150-loop154d.json", rows)
    f_by_id = {r["id"]: r for r in rows138f("probe150-loop138f.json")}
    b_by_id = {r["id"]: r for r in base_rows("probe150-loop138b.json")}
    moves138f, moves = [], []
    for r in rows:
        f = f_by_id.get(r["id"])
        if f is not None and (r["verdict"] != f["verdict"] or
                              r.get("reply") != f.get("reply")):
            moves138f.append({"id": r["id"], "loop138f": f["verdict"],
                              "loop154d": r["verdict"]})
        b = b_by_id.get(r["id"])
        if b is not None and (r["verdict"] != b["verdict"] or
                              r.get("reply") != b.get("reply")):
            moves.append({"id": r["id"], "loop138b": b["verdict"],
                          "loop154d": r["verdict"]})
    return {"suite": "cases150", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138b": moves, "moves_vs_138f": moves138f}


def run_f1(art: Path) -> dict:
    cases = json.loads((ART144 / "f1-cases.json").read_text(
        encoding="utf-8"))["cases"]
    rows = []
    for row in cases:
        t0 = time.time()
        with tempfile.TemporaryDirectory(prefix=row["id"] + "_") as tmp:
            try:
                loop = build154d({"state_dir": tmp,
                                  "sleep_threshold": 100000})
                reply = " ".join(loop.turn(row["text"]))
                stored = [list(t) for t in L90.notebook_triples(loop.nb)]
            except Exception as exc:  # noqa: BLE001
                rows.append({"id": row["id"], "kind": row["kind"],
                             "verdict": "HARNESS-ERROR",
                             "reply": repr(exc)[:120], "stored": []})
                continue
        rep = {"id": row["id"], "kind": row["kind"], "text": row["text"],
               "stored": stored, "reply": reply.strip()[:160],
               "seconds": round(time.time() - t0, 3)}
        if row["kind"] == "must-write":
            want = [list(row["expect"])]
            rep["expect"] = row["expect"]
            if stored == want and reply.strip().startswith("Saved:"):
                rep["verdict"] = "OK"
            elif not stored:
                rep["verdict"] = "MISSED"
            else:
                rep["verdict"] = "WRONG-WRITE"
        else:
            if not stored and not reply.strip().startswith("Saved:"):
                rep["verdict"] = "OK"
            else:
                rep["verdict"] = "WRONG-WRITE"
        rows.append(rep)
    write_rows(art / "f1-loop154d.json", rows)
    f_by_id = {r["id"]: r for r in rows138f("f1-loop138f.json")}
    moves138f = [{"id": r["id"], "loop138f": f_by_id[r["id"]]["verdict"],
                  "loop154d": r["verdict"]} for r in rows
                 if r["id"] in f_by_id and
                 f_by_id[r["id"]]["verdict"] != r["verdict"]]
    return {"suite": "f1", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "non_ok": [r for r in rows if r["verdict"] != "OK"],
            "moves_vs_138f": moves138f}


def run_cases139b(art: Path) -> dict:
    cases = json.loads((ART139B / "cases139b.json").read_text(encoding="utf-8"))
    cases139 = json.loads(
        (ROOT / "artifacts" / "fable-fix139-20260922" / "cases139.json").read_text(
            encoding="utf-8"))
    if isinstance(cases139, dict):
        cases139 = cases139.get("cases", cases139)
    cases = list(cases139) + list(cases)
    rows = [P139b.run_case(row, build154d) for row in cases]
    write_rows(art / "probe139b-loop154d.json", rows)
    f_by_id = {r["id"]: r for r in rows138f("probe139b-loop138f.json")}
    b_by_id = {r["id"]: r for r in base_rows("probe139b-loop138b.json")}
    moves138f, moves = [], []
    for r in rows:
        f = f_by_id.get(r["id"])
        if f is not None and f["verdict"] != r["verdict"]:
            moves138f.append({"id": r["id"], "loop138f": f["verdict"],
                              "loop154d": r["verdict"]})
        b = b_by_id.get(r["id"])
        if b is not None and b["verdict"] != r["verdict"]:
            moves.append({"id": r["id"], "loop138b": b["verdict"],
                          "loop154d": r["verdict"]})
    seven = {}
    for cid in SEVEN["cases139b"]:
        r = {x["id"]: x for x in rows}.get(cid, {})
        b = b_by_id.get(cid, {})
        seven[cid] = (r.get("verdict") == b.get("verdict")
                      and str(r.get("reply", "")).strip()
                      == str(b.get("reply", "")).strip()
                      and r.get("stored", "n/a") == b.get("stored", "n/a"))
    return {"suite": "cases139b", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138b": moves, "moves_vs_138f": moves138f,
            "seven138b": seven}


def run_rt143(art: Path) -> dict:
    R143.Loop132Daemon = L154d.Loop154dDaemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L154d.DEFAULT_CONFIG154D)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = art / "scratch143-loop154d"
    rows: list[dict] = []
    for case in suite["cases"]:
        rows.append(R143.run_case(case, scratch / case["id"], markers))
    (art / "redteam143-loop154d.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    f_base = json.loads(
        (ART138F / "redteam143-loop138f.json").read_text(encoding="utf-8"))
    f_by_id = {r["id"]: r for r in f_base["rows"]}
    b_base = json.loads(
        (ART138B / "redteam143-loop138b.json").read_text(encoding="utf-8"))
    b_by_id = {r["id"]: r for r in b_base["rows"]}
    moves138f, moves, new_wrong = [], [], 0
    for r in rows:
        f = f_by_id.get(r["id"])
        if f is not None and r["verdict"] != f["verdict"]:
            moves138f.append({"id": r["id"], "loop138f": f["verdict"],
                              "loop154d": r["verdict"],
                              "reply154d": str(r.get("reply", ""))[:120]})
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "loop138b": b["verdict"],
                          "loop154d": r["verdict"]})
            if r["verdict"] in ("WRONG-ANSWER", "WRONG") and \
                    b["verdict"] not in ("WRONG-ANSWER", "WRONG"):
                new_wrong += 1
    m3 = next((r for r in rows if r["id"] == "M3"), {})
    b3 = b_by_id.get("M3", {})
    m3_identical = (m3.get("verdict") == b3.get("verdict")
                    and str(m3.get("reply", "")).strip()
                    == str(b3.get("reply", "")).strip())
    return {"suite": "redteam143", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "new_wrong_vs_138b": new_wrong, "moves_vs_138b": moves,
            "moves_vs_138f": moves138f, "M3_identical_to_138b": m3_identical,
            "M3_154d": {k: m3.get(k) for k in ("verdict", "reply")}}


def run_sessions(art: Path) -> dict:
    out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = art / "work-sessions-loop154d" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L154d.DEFAULT_CONFIG154D)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L154d.Loop154dDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        out[s["id"]] = [{**t, "verdict": j["verdict"], "why": j["why"]}
                        for t in turns for j in [S152R.judge(t)]]
    (art / "sessions152-loop154d.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    out138f = json.loads(
        (ART138F / "sessions152-loop138f.json").read_text(encoding="utf-8"))
    moves138f, new_writes = [], []
    c138f: Counter = Counter()
    c154d: Counter = Counter()
    for sid, turns in out.items():
        for t, f in zip(turns, out138f.get(sid, [])):
            c138f[f["verdict"]] += 1
            c154d[t["verdict"]] += 1
            if t["verdict"] != f["verdict"]:
                moves138f.append({"session": sid, "n": t["n"],
                                  "text": str(t["text"])[:100],
                                  "loop138f": f["verdict"],
                                  "loop154d": t["verdict"],
                                  "reply154d": str(t["reply"]).strip()[:120]})
            fw = (f.get("fact_writes") or f.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != fw:
                new_writes.append({"session": sid, "n": t["n"],
                                   "loop138f_writes": fw,
                                   "loop154d_writes": tw})
    return {"suite": "sessions152", "loop138f": dict(c138f),
            "loop154d": dict(c154d), "moves_vs_138f": moves138f,
            "new_writes_vs_138f": new_writes}


def run_bench(art: Path) -> dict:
    data134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
    data132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"
    splits = (
        ("new_121_4hop", B.DATA_NEW,
         "fable_bench121_loop138b_new_121_4hop_rows.jsonl",
         "fable_bench121_loop138f_new_121_4hop_rows.jsonl"),
        ("old_s2fresh_4hop", B.DATA_OLD,
         "fable_bench121_loop138b_old_s2fresh_4hop_rows.jsonl",
         "fable_bench121_loop138f_old_s2fresh_4hop_rows.jsonl"),
        ("edit200", data134,
         "fable_bench121_loop138b_edit200_rows.jsonl",
         "fable_bench121_loop138f_edit200_rows.jsonl"),
        ("bench132_4hop", data132,
         "fable_bench121_loop138b_bench132_4hop_rows.jsonl",
         "fable_bench121_loop138f_bench132_4hop_rows.jsonl"),
    )
    B.Loop121Daemon = L154d.Loop154dDaemon  # type: ignore[method-assign]
    cfg = copy.deepcopy(L154d.DEFAULT_CONFIG154D)
    cfg["sleep_threshold"] = 100000
    workroot = art / "scratch-bench121-loop154d"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    summary: dict = {"agent": "loop154d", "splits": {}}
    rc = 0
    for stag, path, sealed138b, sealed138f in splits:
        items = [json.loads(l) for l in Path(str(path)).read_text(
            encoding="utf-8").splitlines() if l.strip()]
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (art / f"fable_bench121_loop154d_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        s_by_id = {r["id"]: r for r in
                   (json.loads(l) for l in
                    (ART138B / sealed138b).read_text(
                        encoding="utf-8").splitlines() if l.strip())}
        f_by_id = {r["id"]: r for r in
                   (json.loads(l) for l in
                    (ART138F / sealed138f).read_text(
                        encoding="utf-8").splitlines() if l.strip())}
        moves, moves138f, new_wrong = [], [], 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is not None and r["verdict"] != s["verdict"]:
                moves.append({"id": r["id"], "loop138b": s["verdict"],
                              "loop154d": r["verdict"]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
            f = f_by_id.get(r["id"])
            if f is not None and (r["verdict"] != f["verdict"] or
                                  r.get("reply") != f.get("reply")):
                moves138f.append({"id": r["id"], "loop138f": f["verdict"],
                                  "loop154d": r["verdict"]})
        if new_wrong:
            rc = 1
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        summary["splits"][stag] = {**cell, "new_wrong_vs_138b": new_wrong,
                                   "moves_vs_138b": moves,
                                   "moves_vs_138f": moves138f}
        print(f"{stag}: loop154d {cell} new_wrong={new_wrong} "
              f"moves138f={len(moves138f)}", flush=True)
        for m in moves138f:
            print(f"  MOVE138f {m['id']}: {m['loop138f']} -> {m['loop154d']}",
                  flush=True)
    summary["rc"] = rc
    (art / "fable_bench121_summary_loop154d.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    return {"suite": "bench", **summary}


FUNCS = {"redteam136": run_redteam136, "cases150": run_cases150,
         "f1": run_f1, "cases139b": run_cases139b, "redteam143": run_rt143,
         "sessions152": run_sessions, "bench": run_bench}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 154d frozen suites")
    ap.add_argument("--suite", default="all",
                    help="comma list or 'all'")
    ap.add_argument("--art", default=str(ART))
    args = ap.parse_args(argv)
    art = Path(args.art)
    art.mkdir(parents=True, exist_ok=True)
    want = list(FUNCS) if args.suite == "all" else args.suite.split(",")
    t0 = time.time()
    out: dict = {}
    rc = 0
    for name in want:
        rep = FUNCS[name](art)
        out[rep["suite"]] = rep
        print(f"154d {rep['suite']}: "
              f"{rep.get('counter', rep.get('loop154d', ''))} "
              f"moves138f={len(rep.get('moves_vs_138f', []))}", flush=True)
        for m in rep.get("moves_vs_138f", []) or []:
            print(f"  MOVE138f {m}", flush=True)
        for key in ("moves_vs_138b", "moves"):
            for m in rep.get(key, []) or []:
                got = m.get("loop154d", "")
                if got in ("WRONG-WRITE", "WRONG-ANSWER", "WRONG-REPLY",
                           "WRONG", "wrong"):
                    rc = 1
        if rep.get("new_wrong_vs_138b"):
            rc = 1
        if rep.get("new_writes_vs_138f"):
            rc = 1
        for cid, ok in (rep.get("seven138b") or {}).items():
            if not ok:
                rc = 1
        if "M3_identical_to_138b" in rep and \
                not rep["M3_identical_to_138b"]:
            rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    (art / "suites154d-summary.json").write_text(
        json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    print(f"154d suites {out['seconds']}s rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
