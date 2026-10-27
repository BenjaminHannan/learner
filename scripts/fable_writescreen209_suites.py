#!/usr/bin/env python3
"""Experiment 209 -- W3 frozen suites + bench driver (Muse).

Runs redteam136, redteam143, sessions152, and bench-v3 on loop209 ONLY
and compares per-case against loop138i's SEALED rows (read-only):

  g2frozen/redteam136-loop138i.json (JSONL rows)
  g2frozen/redteam143-loop138i.json ({"rows": [...]})
  g2frozen/sessions152-loop138i.json ({sid: turns})
  g1bench/fable_benchv3_loop138i_<split>_rows.jsonl

Move = verdict, reply, or stored/writes differ vs the sealed 138i row.
new_wrong = sealed row not WRONGish and 209 row WRONGish.
Bar (see PASSMARKS.md): 0 new WRONG/WRONG-WRITE/junk writes; moves only
the ids listed in writing before the seal.

Pilot use: --out <scratch dir> (outside artifacts/).
Registered use (only AFTER PASSMARKS.md is sealed): --out
artifacts/fable-writescreen209-20260922/suites (small JSON only; row
files stay small, scratch deleted).

Run (Mac CPU, offline; heavy suites one at a time):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_writescreen209_suites.py --only <rt136|rt143|sessions|bench> --out <dir>
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

import fable_loop209_agent as L209  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART138I = ROOT / "artifacts" / "fable-agent138i-20260922"

WRONGish = ("WRONG-WRITE", "WRONG-ANSWER", "WRONG", "WRONG-REPLY", "BUG",
            "wrong")

OUTDIR = Path(".")


def new_daemon209(root: Path):
    cfg = copy.deepcopy(L209.DEFAULT_CONFIG209)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L209.Loop209Daemon(root, cfg=cfg, idle_seconds=3600.0)


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False),
                    encoding="utf-8")


def run_rt136(out: Path) -> dict:
    import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
    t0 = time.time()
    R136.new_daemon139b = new_daemon209  # type: ignore[method-assign]
    cases = json.loads((ROOT / "artifacts" / "fable-redteam136-20260922"
                        / "cases136.json").read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = Path(tempfile.mkdtemp(prefix="w209-rt136-"))
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_json(out / "redteam136-loop209.json", rows)
    base = [json.loads(line) for line in
            (ART138I / "g2frozen" / "redteam136-loop138i.json").read_text(
                encoding="utf-8").splitlines() if line.strip()]
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            moves.append({"id": r["id"], "what": "missing-base"})
            continue
        if (r["verdict"] != b["verdict"]
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()
                or r.get("stored") != b.get("stored")):
            moves.append({"id": r["id"], "loop138i": b["verdict"],
                          "loop209": r["verdict"],
                          "reply138i": str(b.get("reply", ""))[:140],
                          "reply209": str(r.get("reply", ""))[:140],
                          "stored138i": b.get("stored"),
                          "stored209": r.get("stored")})
            if b["verdict"] not in WRONGish and r["verdict"] in WRONGish:
                new_wrong += 1
    shutil.rmtree(workroot, ignore_errors=True)
    rep = {"suite": "redteam136", "n": len(rows),
           "counter": dict(Counter(r["verdict"] for r in rows)),
           "moves": moves, "new_wrong": new_wrong,
           "seconds": round(time.time() - t0, 1)}
    write_json(out / "rt136-report.json", rep)
    print(f"rt136: {rep['counter']} moves={len(moves)} "
          f"new_wrong={new_wrong}", flush=True)
    for m in moves[:20]:
        print(f"  MOVE {m}", flush=True)
    return rep


def run_rt143(out: Path) -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    t0 = time.time()
    R143.Loop132Daemon = L209.Loop209Daemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L209.DEFAULT_CONFIG209)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = Path(tempfile.mkdtemp(prefix="w209-rt143-"))
    rows = [R143.run_case(c, scratch / c["id"], markers)
            for c in suite["cases"]]
    write_json(out / "redteam143-loop209.json", {"rows": rows})
    base = json.loads((ART138I / "g2frozen" / "redteam143-loop138i.json")
                      .read_text(encoding="utf-8"))
    b_by_id = {r["id"]: r for r in base["rows"]}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            moves.append({"id": r["id"], "what": "missing-base"})
            continue
        if (r["verdict"] != b["verdict"]
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()):
            moves.append({"id": r["id"], "loop138i": b["verdict"],
                          "loop209": r["verdict"],
                          "reply138i": str(b.get("reply", ""))[:140],
                          "reply209": str(r.get("reply", ""))[:140]})
            if b["verdict"] not in WRONGish and r["verdict"] in WRONGish:
                new_wrong += 1
    shutil.rmtree(scratch, ignore_errors=True)
    rep = {"suite": "redteam143", "n": len(rows),
           "counter": dict(Counter(r["verdict"] for r in rows)),
           "moves": moves, "new_wrong": new_wrong,
           "seconds": round(time.time() - t0, 1)}
    write_json(out / "rt143-report.json", rep)
    print(f"rt143: {rep['counter']} moves={len(moves)} "
          f"new_wrong={new_wrong}", flush=True)
    for m in moves[:20]:
        print(f"  MOVE {m}", flush=True)
    return rep


def run_sessions(out: Path) -> dict:
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    t0 = time.time()
    sessions_out: dict = {}
    workroot = Path(tempfile.mkdtemp(prefix="w209-s152-"))
    for s in S152R.S152.SESSIONS:
        root = workroot / s["id"]
        root.mkdir(parents=True)
        daemon = new_daemon209(root)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    write_json(out / "sessions152-loop209.json", sessions_out)
    out138i = json.loads((ART138I / "g2frozen" / "sessions152-loop138i.json")
                         .read_text(encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, []
    counts138i: Counter = Counter()
    counts209: Counter = Counter()
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, out138i.get(sid, [])):
            counts138i[b["verdict"]] += 1
            counts209[t["verdict"]] += 1
            if (t["verdict"] != b["verdict"]
                    or str(t.get("reply", "")).strip()
                    != str(b.get("reply", "")).strip()):
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138i": b["verdict"],
                              "loop209": t["verdict"],
                              "reply138i": str(b["reply"]).strip()[:120],
                              "reply209": str(t["reply"]).strip()[:120],
                              "why": t["why"][:160]})
                if (t["verdict"] == "WRONG"
                        and b["verdict"] != "WRONG"):
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"],
                                   "loop138i_writes": bw,
                                   "loop209_writes": tw})
    shutil.rmtree(workroot, ignore_errors=True)
    rep = {"suite": "sessions", "loop138i": dict(counts138i),
           "loop209": dict(counts209), "moves": moves,
           "new_wrong": new_wrong, "new_writes": new_writes,
           "seconds": round(time.time() - t0, 1)}
    write_json(out / "sessions-report.json", rep)
    print(f"sessions: {dict(counts209)} moves={len(moves)} "
          f"new_wrong={new_wrong} new_writes={len(new_writes)}", flush=True)
    for m in moves[:20]:
        print(f"  MOVE {m}", flush=True)
    for w in new_writes[:20]:
        print(f"  WRITE {w}", flush=True)
    return rep


def run_bench(out: Path, only: str = "all") -> dict:
    import fable_bench121_run as B  # noqa: E402 (scorer, read-only)
    import fable_fix172b_benchv3 as V3  # noqa: E402 (v3 driver, read-only)
    t0 = time.time()
    splits = (
        ("new_121_4hop", B.DATA_NEW,
         "fable_benchv3_loop138i_new_121_4hop_rows.jsonl"),
        ("old_s2fresh_4hop", B.DATA_OLD,
         "fable_benchv3_loop138i_old_s2fresh_4hop_rows.jsonl"),
        ("edit200", str(ROOT / "data" / "open" / "bench65"
                        / "fable_edit_200.jsonl"),
         "fable_benchv3_loop138i_edit200_rows.jsonl"),
        ("bench132_4hop", str(ROOT / "data" / "open" / "bench132"
                              / "fable_edit132_4hop.jsonl"),
         "fable_benchv3_loop138i_bench132_4hop_rows.jsonl"),
    )
    if only != "all":
        splits = [s for s in splits if s[0] in only.split(",")]
    workroot = Path(tempfile.mkdtemp(prefix="w209-bench-"))
    summary: dict = {"seconds": 0.0, "arm": "loop209", "proto": "v3",
                     "splits": {}}
    for stag, path, sealed_name in splits:
        items = [json.loads(line) for line in
                 Path(str(path)).read_text(
                     encoding="utf-8").splitlines() if line.strip()]
        cfg = copy.deepcopy(L209.DEFAULT_CONFIG209)
        cfg["sleep_threshold"] = 100000
        rows = [V3.run_item_v3(it, workroot / stag, copy.deepcopy(cfg),
                               L209.Loop209Daemon, "v3") for it in items]
        (out / f"fable_benchv3_loop209_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong"),
                "confirms": sum(r["confirms"] for r in rows)}
        base_rows_l = [json.loads(line) for line in
                       (ART138I / "g1bench" / sealed_name).read_text(
                           encoding="utf-8").splitlines() if line.strip()]
        s_by_id = {r["id"]: r for r in base_rows_l}
        moves, new_wrong = [], 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                moves.append({"id": r["id"], "loop138i": s["verdict"],
                              "loop209": r["verdict"],
                              "reply138i": str(s.get("reply", ""))[:120],
                              "reply209": str(r.get("reply", ""))[:120]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        summary["splits"][stag] = {"loop209": cell,
                                   "moves_vs_138i": moves,
                                   "new_wrong_vs_138i": new_wrong}
        print(f"v3 {stag}: loop209 {cell} new_wrong={new_wrong} "
              f"moves={len(moves)}", flush=True)
        for m in moves[:16]:
            print(f"  MOVE {m}", flush=True)
    shutil.rmtree(workroot, ignore_errors=True)
    summary["seconds"] = round(time.time() - t0, 1)
    write_json(out / "bench-report.json", summary)
    return summary


def main(argv=None) -> int:
    global OUTDIR
    ap = argparse.ArgumentParser(description="Exp 209 W3 suites")
    ap.add_argument("--only", default="all",
                    choices=["all", "rt136", "rt143", "sessions", "bench"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--bench-only", default="all")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    OUTDIR = out
    reps = {}
    if args.only in ("all", "rt136"):
        reps["rt136"] = run_rt136(out)
    if args.only in ("all", "rt143"):
        reps["rt143"] = run_rt143(out)
    if args.only in ("all", "sessions"):
        reps["sessions"] = run_sessions(out)
    if args.only in ("all", "bench"):
        reps["bench"] = run_bench(out, args.bench_only)
    ok = all(r.get("new_wrong", r.get("new_wrong_vs_138i", 0)) == 0
             for r in reps.values())
    print(json.dumps({k: "OK" for k in reps}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
