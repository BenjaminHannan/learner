#!/usr/bin/env python3
"""Exp 180 T2 -- frozen suites through loop180, diffed vs sealed loop138g rows.

Reuses the sealed judges/harnesses read-only (same cases, same judges as
the 138g runs); only the loop under test is loop180. Compares verdict +
reply (+stored/writes) per case vs the SEALED 138g rows. Predicted: 0
moves, 0 new WRONG/WRONG-WRITE/junk writes everywhere.

Outputs into artifacts/fable-lowercase180-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; ONE suite at a
time under parallel-agent load):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix180_suites.py --only rt136|rt143|sessions|bench|all
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop180_agent as L180  # noqa: E402 (agent under test)
import fable_fix138g_suites as G138  # noqa: E402 (helpers, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-lowercase180-20260922"
ART138G = ROOT / "artifacts" / "fable-agent138g-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"


def sealed138g(name: str):
    p = ART138G / name
    txt = p.read_text(encoding="utf-8")
    try:
        d = json.loads(txt)
        if isinstance(d, dict) and "rows" in d:
            return d["rows"]
        return d
    except Exception:
        return [json.loads(l) for l in txt.splitlines() if l.strip()]


def new_daemon180(root: Path):
    cfg = copy.deepcopy(L180.DEFAULT_CONFIG180)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L180.Loop180Daemon(root, cfg=cfg, idle_seconds=3600.0)


def run_rt136() -> dict:
    import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
    R136.new_daemon139b = new_daemon180  # type: ignore[method-assign]
    cases = json.loads(
        (ROOT / "artifacts" / "fable-redteam136-20260922"
         / "cases136.json").read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    G138.write_rows(ART / "redteam136-loop180.json", rows)
    base = sealed138g("redteam136-loop138g.json")
    moves, _ = G138.moves_vs(rows, base, "loop180")
    base_b = [json.loads(l) for l in
              (ART138B / "redteam136-loop138b.json").read_text(
                  encoding="utf-8").splitlines() if l.strip()]
    _, new_wrong_b = G138.moves_vs(rows, base_b, "loop180")
    rep = {"suite": "redteam136", "n": len(rows),
           "counter": dict(Counter(r["verdict"] for r in rows)),
           "moves_vs_138g": moves, "new_wrong_vs_138b": new_wrong_b}
    print(f"rt136: n={rep['n']} {rep['counter']} "
          f"moves_vs_138g={len(moves)} new_wrong_vs_138b={new_wrong_b}",
          flush=True)
    for m in moves:
        print(f"  MOVE {m}", flush=True)
    return rep


def run_rt143() -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    R143.Loop132Daemon = L180.Loop180Daemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L180.DEFAULT_CONFIG180)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop180"
    rows: list[dict] = []
    for case in suite["cases"]:
        rows.append(R143.run_case(case, scratch / case["id"], markers))
    (ART / "redteam143-loop180.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base = sealed138g("redteam143-loop138g.json")
    moves, _ = G138.moves_vs(rows, base, "loop180")
    rep = {"suite": "rt143", "n": len(rows),
           "counter": dict(Counter(r["verdict"] for r in rows)),
           "moves_vs_138g": moves}
    print(f"rt143: n={rep['n']} {rep['counter']} "
          f"moves_vs_138g={len(moves)}", flush=True)
    for m in moves:
        print(f"  MOVE {m}", flush=True)
    return rep


def run_sessions() -> dict:
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop180" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L180.DEFAULT_CONFIG180)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L180.Loop180Daemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (ART / "sessions152-loop180.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    out138g = json.loads(
        (ART138G / "sessions152-loop138g.json").read_text(encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, []
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, out138g.get(sid, [])):
            if t["verdict"] != b["verdict"] or str(t.get("reply")) != str(
                    b.get("reply")):
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138g": b["verdict"],
                              "loop180": t["verdict"],
                              "reply138g": str(b["reply"]).strip()[:120],
                              "reply180": str(t["reply"]).strip()[:120]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"],
                                   "loop138g_writes": bw,
                                   "loop180_writes": tw})
    rep = {"suite": "sessions", "moves_vs_138g": moves,
           "new_wrong_vs_138g": new_wrong, "new_writes": new_writes}
    print(f"sessions: moves_vs_138g={len(moves)} new_wrong={new_wrong} "
          f"new_writes={len(new_writes)}", flush=True)
    for m in moves:
        print(f"  MOVE {m}", flush=True)
    return rep


def run_bench(only: str = "all") -> dict:
    import fable_bench121_run as B  # noqa: E402 (scorer, read-only)
    B.Loop121Daemon = L180.Loop180Daemon
    cfg = copy.deepcopy(L180.DEFAULT_CONFIG180)
    cfg["sleep_threshold"] = 100000
    tag = "loop180"
    DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
    DATA132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"
    splits = (
        ("new_121_4hop", B.DATA_NEW,
         "fable_bench121_loop138g_new_121_4hop_rows.jsonl"),
        ("old_s2fresh_4hop", B.DATA_OLD,
         "fable_bench121_loop138g_old_s2fresh_4hop_rows.jsonl"),
        ("edit200", DATA134, "fable_bench121_loop138g_edit200_rows.jsonl"),
        ("bench132_4hop", DATA132,
         "fable_bench121_loop138g_bench132_4hop_rows.jsonl"),
    )
    want = only.split(",")
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = ART / "scratch-bench121-loop180"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    summary: dict = {"agent": tag, "splits": {}}
    for stag, path, sealed_name in splits:
        items = [json.loads(line) for line in
                 Path(str(path)).read_text(
                     encoding="utf-8").splitlines() if line.strip()]
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (ART / f"fable_bench121_{tag}_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        base_l = [json.loads(line) for line in
                  (ART138G / sealed_name).read_text(
                      encoding="utf-8").splitlines() if line.strip()]
        s_by_id = {r["id"]: r for r in base_l}
        moves, new_wrong = [], 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                moves.append({"id": r["id"], "loop138g": s["verdict"],
                              tag: r["verdict"]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        summary["splits"][stag] = {"n": len(rows),
                                   "moves_vs_138g": moves,
                                   "new_wrong_vs_138g": new_wrong}
        print(f"{stag}: n={len(rows)} moves_vs_138g={len(moves)} "
              f"new_wrong={new_wrong}", flush=True)
        for m in moves:
            print(f"  MOVE {m}", flush=True)
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 180 T2 suites")
    ap.add_argument("--only", default="all",
                    help="rt136|rt143|sessions|bench|all (bench splits: "
                    "append :split with run_bench only mode unsupported; "
                    "use all)")
    args = ap.parse_args(argv)
    t0 = time.time()
    out: dict = {}
    only = args.only
    if only in ("all", "rt136"):
        out["rt136"] = run_rt136()
    if only in ("all", "rt143"):
        out["rt143"] = run_rt143()
    if only in ("all", "sessions"):
        out["sessions"] = run_sessions()
    if only in ("all", "bench"):
        out["bench"] = run_bench()
    out["seconds"] = round(time.time() - t0, 1)
    (ART / f"t2-{only}-loop180.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False)[:200000],
        encoding="utf-8")
    bad = any(len(v.get("moves_vs_138g", [])) > 0
              or v.get("new_wrong_vs_138b", 0) > 0
              or v.get("new_wrong_vs_138g", 0) > 0
              or len(v.get("new_writes", [])) > 0
              for v in out.values() if isinstance(v, dict))
    for _v in [v for v in out.values()
               if isinstance(v, dict) and "splits" in v]:
        for _s in _v["splits"].values():
            if _s.get("moves_vs_138g") or _s.get("new_wrong_vs_138g"):
                bad = True
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
