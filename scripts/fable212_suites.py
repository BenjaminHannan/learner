#!/usr/bin/env python3
"""Exp 212 M3 driver -- frozen suites + marks123 + bench v3 + self panel.

Compares loop212 per-case against the SEALED loop138i rows (read-only):
  rt136 (145) vs g2frozen/redteam136-loop138i.json
  rt143 (124) vs g2frozen/redteam143-loop138i.json
  sessions152 vs g2frozen/sessions152-loop138i.json
  benchv3 (4 splits x 200) vs g1bench/fable_benchv3_loop138i_*_rows.jsonl
  marks123 (stock CLI, one suite at a time) vs marks138i/*-report.json
  self105 panel scorer (frozen code, untouched by 212) vs sealed counts
Predicted: 0 moves everywhere (no ids listed); 0 new WRONG/WRONG-WRITE/
junk writes; bench 0 new wrong.

Run (Mac CPU, offline; only AFTER PASSMARKS sealed for registered runs;
pilots use --out outside artifacts/; heavy suites one at a time):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable212_suites.py --only <rt136|rt143|sessions|benchv3|marks|selfpanel|all> --out <dir>
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix138g_suites as G138  # noqa: E402 (helpers, read-only)
import fable_loop212_agent as L212  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-selfgate212-20260922"
ART138I = ROOT / "artifacts" / "fable-agent138i-20260922"
TAG = "loop212"

WRONGish = ("WRONG-WRITE", "WRONG-ANSWER", "WRONG", "WRONG-REPLY", "BUG",
            "wrong")

MARKS_SUITES = ["p2", "p3", "p4", "rt110", "q1", "bench", "rt81",
                "sleep", "soak"]
MARKS_REPORT = {"p2": "p2-report.json", "p3": "p3-report.json",
                "p4": "p4-report.json", "rt110": "rt110-report.json",
                "q1": "q1-report.json", "bench": "bench-report.json",
                "rt81": "rt81-report.json", "sleep": "sleep-report.json",
                "soak": "soak-report.json", "q4": "q4-report.json"}

OUTDIR = ART


def new_daemon212(root: Path):
    cfg = copy.deepcopy(L212.DEFAULT_CONFIG212)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L212.Loop212Daemon(root, cfg=cfg, idle_seconds=3600.0)


def sealed(name: str, sub: str):
    p = ART138I / sub / name
    txt = p.read_text(encoding="utf-8")
    try:
        d = json.loads(txt)
        if isinstance(d, dict) and "rows" in d:
            return d["rows"]
        return d
    except Exception:
        return [json.loads(line) for line in txt.splitlines()
                if line.strip()]


def run_rt136() -> dict:
    import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
    R136.new_daemon139b = new_daemon212  # type: ignore[method-assign]
    cases = json.loads((ROOT / "artifacts" / "fable-redteam136-20260922"
                        / "cases136.json").read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = OUTDIR / "work-rt136"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    G138.write_rows(OUTDIR / "redteam136-loop212.json", rows)
    base = sealed("redteam136-loop138i.json", "g2frozen")
    moves, new_wrong = G138.moves_vs(rows, base, TAG)
    print(f"rt136: {dict(Counter(r['verdict'] for r in rows))} "
          f"moves={len(moves)} new_wrong={new_wrong}", flush=True)
    for m in moves[:20]:
        print(f"  MOVE {m}", flush=True)
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138i": moves, "new_wrong_vs_138i": new_wrong}


def run_rt143() -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    R143.Loop132Daemon = L212.Loop212Daemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L212.DEFAULT_CONFIG212)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = OUTDIR / "scratch143-loop212"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    rows = [R143.run_case(case, scratch / case["id"], markers)
            for case in suite["cases"]]
    (OUTDIR / "redteam143-loop212.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base = sealed("redteam143-loop138i.json", "g2frozen")
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if (r["verdict"] != b["verdict"]
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()):
            moves.append({"id": r["id"], "loop138i": b["verdict"],
                          TAG: r["verdict"],
                          "reply138i": str(b.get("reply", ""))[:140],
                          "reply212": str(r.get("reply", ""))[:140]})
            if b["verdict"] not in WRONGish and r["verdict"] in WRONGish:
                new_wrong += 1
    print(f"rt143: {dict(Counter(r['verdict'] for r in rows))} "
          f"moves={len(moves)} new_wrong={new_wrong}", flush=True)
    for m in moves[:20]:
        print(f"  MOVE {m}", flush=True)
    return {"suite": "redteam143", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138i": moves, "new_wrong_vs_138i": new_wrong}


def run_sessions() -> dict:
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = OUTDIR / "work-sessions-loop212" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        daemon = new_daemon212(root)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (OUTDIR / "sessions152-loop212.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    out138i = sealed("sessions152-loop138i.json", "g2frozen")
    moves, new_wrong, new_writes = [], 0, []
    counts138i: Counter = Counter()
    counts212: Counter = Counter()
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, out138i.get(sid, [])):
            counts138i[b["verdict"]] += 1
            counts212[t["verdict"]] += 1
            if (t["verdict"] != b["verdict"]
                    or str(t.get("reply", "")).strip()
                    != str(b.get("reply", "")).strip()):
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138i": b["verdict"],
                              TAG: t["verdict"],
                              "reply138i": str(b["reply"]).strip()[:120],
                              "reply212": str(t["reply"]).strip()[:120],
                              "why": t["why"][:160]})
                if (t["verdict"] == "WRONG"
                        and b["verdict"] != "WRONG"):
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"],
                                   "loop138i_writes": bw,
                                   "loop212_writes": tw})
    print(f"sessions: {dict(counts212)} moves={len(moves)} "
          f"new_wrong={new_wrong} new_writes={len(new_writes)}", flush=True)
    for m in moves[:20]:
        print(f"  MOVE {m}", flush=True)
    for w in new_writes[:20]:
        print(f"  WRITE {w}", flush=True)
    return {"suite": "sessions", "loop138i": dict(counts138i),
            TAG: dict(counts212), "moves_vs_138i": moves,
            "new_wrong_vs_138i": new_wrong, "new_writes": new_writes}


def run_benchv3(only: str = "all") -> dict:
    import fable_bench121_run as B  # noqa: E402 (scorer, read-only)
    import fable_fix172b_benchv3 as V3  # noqa: E402 (v3 driver, read-only)
    daemon_cls, cfg0 = L212.Loop212Daemon, L212.DEFAULT_CONFIG212
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
    want = only.split(",")
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = OUTDIR / "scratch-benchv3-loop212"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    summary: dict = {"seconds": 0.0, "arm": TAG, "proto": "v3", "splits": {}}
    for stag, path, sealed_name in splits:
        items = [json.loads(line) for line in
                 Path(str(path)).read_text(
                     encoding="utf-8").splitlines() if line.strip()]
        cfg = copy.deepcopy(cfg0)
        cfg["sleep_threshold"] = 100000
        rows = [V3.run_item_v3(it, workroot / stag, copy.deepcopy(cfg),
                               daemon_cls, "v3") for it in items]
        (OUTDIR / f"fable_benchv3_{TAG}_{stag}_rows.jsonl").write_text(
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
            if (r["verdict"] != s["verdict"]
                    or str(r.get("reply", "")).strip()
                    != str(s.get("reply", "")).strip()):
                moves.append({"id": r["id"], "loop138i": s["verdict"],
                              TAG: r["verdict"],
                              "reply138i": str(s.get("reply", ""))[:120],
                              "reply212": str(r.get("reply", ""))[:120]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        summary["splits"][stag] = {TAG: cell,
                                   "moves_vs_138i": moves,
                                   "new_wrong_vs_138i": new_wrong}
        print(f"v3 {stag}: {TAG} {cell} new_wrong={new_wrong} "
              f"moves={len(moves)}", flush=True)
        for m in moves[:16]:
            print(f"  MOVE {m}", flush=True)
    return summary


VOLATILE_KEYS = {"seconds", "total_seconds", "started", "finished",
                 "summary_total_seconds"}


def _scrub_str(s: str) -> str:
    for old, new in (
            ("fable-selfgate212-20260922", "ART_DIR"),
            ("fable-agent138i-20260922", "ART_DIR"),
            ("scripts/fable_loop212_agent.py", "scripts/AGENT.py"),
            ("scripts/fable_loop138i_agent.py", "scripts/AGENT.py"),
            ("fable_loop212_agent.py", "AGENT.py"),
            ("fable_loop138i_agent.py", "AGENT.py"),
            ("loop212-config.json", "CONFIG.json"),
            ("loop138i-config.json", "CONFIG.json")):
        s = s.replace(old, new)
    return s


def _scrub(obj):
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()
                if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, str):
        return _scrub_str(obj)
    if isinstance(obj, float):
        return round(obj, 1)
    return obj


def _rows_by_id(rows):
    return {str(r.get("id", i)): r for i, r in enumerate(rows)}


def compare_row_lists(base_rows, got_rows) -> list:
    """Per-case compare: verdict-ish keys + reply-ish text. Returns moves."""
    moves: list = []
    b_by = _rows_by_id(base_rows)
    for i, r in enumerate(got_rows):
        key = str(r.get("id", i))
        b = b_by.get(key)
        if b is None:
            moves.append({"id": key, "kind": "new-row"})
            continue
        for vkey in ("agent_verdict", "verdict", "pass", "sealed_verdict"):
            if vkey in b or vkey in r:
                if b.get(vkey) != r.get(vkey):
                    moves.append({"id": key, "key": vkey,
                                  "base": b.get(vkey), "got": r.get(vkey)})
        for tkey in ("agent_final", "reply", "observed"):
            if tkey in b or tkey in r:
                if _scrub_str(str(b.get(tkey, ""))) != _scrub_str(
                        str(r.get(tkey, ""))):
                    moves.append({"id": key, "key": tkey,
                                  "base": str(b.get(tkey, ""))[:160],
                                  "got": str(r.get(tkey, ""))[:160]})
    return moves


def compare_bench_rows(out: Path) -> list:
    """Per-item verdict+reply compare of the stock bench rows jsonl."""
    moves: list = []
    for name in ("bench-rows-fable_edit_200.jsonl",
                 "bench-rows-s2fresh_4hop.jsonl"):
        try:
            got = [json.loads(line) for line in
                   (out / name).read_text(encoding="utf-8").splitlines()
                   if line.strip()]
            base = [json.loads(line) for line in
                    (ART138I / "marks138i" / name).read_text(
                        encoding="utf-8").splitlines() if line.strip()]
        except OSError as exc:
            return [{"bench-rows": f"missing file {name}: {exc}"}]
        b_by = {r["id"]: r for r in base}
        for r in got:
            s = b_by.get(r["id"])
            if s is None:
                moves.append({"id": r["id"], "kind": "new-row"})
            elif (r.get("verdict") != s.get("verdict")
                    or str(r.get("reply", "")).strip() != str(
                        s.get("reply", "")).strip()):
                moves.append({"id": r["id"], "key": "verdict/reply",
                              "base": s.get("verdict"),
                              "got": r.get("verdict"),
                              "reply_base": str(s.get("reply", ""))[:120],
                              "reply_got": str(r.get("reply", ""))[:120]})
    return moves


def compare_marks_reports(suite: str, base: dict, got: dict,
                            out: Path | None = None) -> list:
    """Per-case compare with volatile scrub; sleep agent-rename allowed."""
    moves: list = []
    if suite == "sleep":
        gb, gg = _scrub(base), _scrub(got)
        if gb == gg:
            return []
        return [{"sleep": "diff-after-scrub",
                 "base": str(base)[:300], "got": str(got)[:300]}]
    if suite == "bench" and out is not None:
        moves = compare_bench_rows(out)
        gb, gg = _scrub(base), _scrub(got)
        if gb != gg:
            moves.append({"suite": suite, "kind": "report-diff",
                          "base": str(gb)[:300], "got": str(gg)[:300]})
        return moves
    brows = base.get("rows", base.get("cases"))
    grows = got.get("rows", got.get("cases"))
    if isinstance(brows, list) and isinstance(grows, list):
        return compare_row_lists(brows, grows)
    gb, gg = _scrub(base), _scrub(got)
    if gb != gg:
        moves.append({"suite": suite, "kind": "report-diff",
                      "base_keys": sorted(base.keys()),
                      "got_keys": sorted(got.keys())})
    return moves


def run_marks(only_suites: str = "all") -> dict:
    out = OUTDIR / "marks212"
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    cmp_rep: dict = {}
    suites = MARKS_SUITES if only_suites == "all" else only_suites.split(",")
    for suite in suites:
        cmd = [sys.executable, "-B",
               str(SCRIPTS / "fable_marks123_all.py"),
               "--agent", "scripts/fable_loop212_agent.py",
               "--config", str(ART / "loop212-config.json"),
               "--out", str(out), "--suite", suite,
               "--workers", "1"]
        p = subprocess.run(cmd, capture_output=True, text=True, env=env,
                           cwd=str(ROOT))
        sys.stdout.write(p.stdout[-2000:])
        sys.stderr.write(p.stderr[-800:])
        if p.returncode not in (0, 1):
            cmp_rep[suite] = {"error": f"runner rc={p.returncode}",
                              "pass": False}
            print(f"marks-{suite}: RUNNER ERROR rc={p.returncode}",
                  flush=True)
            continue
        rep_path = out / MARKS_REPORT[suite]
        base_path = ART138I / "marks138i" / MARKS_REPORT[suite]
        try:
            got = json.loads(rep_path.read_text(encoding="utf-8"))
            base = json.loads(base_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            cmp_rep[suite] = {"error": str(exc), "pass": False}
            continue
        moves = compare_marks_reports(suite, base, got, out)
        cmp_rep[suite] = {"pass": not moves, "moves": moves,
                          "got_pass": got.get("pass"),
                          "base_pass": base.get("pass")}
        print(f"marks-{suite}: base_pass={base.get('pass')} "
              f"got_pass={got.get('pass')} moves={len(moves)}", flush=True)
        for m in moves[:20]:
            print(f"  MOVE {m}", flush=True)
    # q4 is derived by the stock runner from collected replies (no agent
    # run of its own): reuse it read-only over this out dir, then compare.
    import fable_marks123_all as M123  # noqa: E402 (read-only reuse)
    try:
        q4rep = M123.suite_q4(out, M123.collect_replies(out))
        q4base = json.loads((ART138I / "marks138i" / "q4-report.json")
                            .read_text(encoding="utf-8"))
        q4moves = compare_row_lists(
            [{"id": "q4", "leaks": q4base.get("leaks", [])}],
            [{"id": "q4", "leaks": q4rep.get("leaks", [])}])
        if q4base.get("pass") != q4rep.get("pass"):
            q4moves.append({"id": "q4", "key": "pass",
                            "base": q4base.get("pass"),
                            "got": q4rep.get("pass")})
        cmp_rep["q4"] = {"pass": not q4moves, "moves": q4moves,
                         "got_pass": q4rep.get("pass"),
                         "base_pass": q4base.get("pass")}
        print(f"marks-q4: base_pass={q4base.get('pass')} "
              f"got_pass={q4rep.get('pass')} moves={len(q4moves)}",
              flush=True)
    except (OSError, ValueError) as exc:
        cmp_rep["q4"] = {"error": str(exc), "pass": False}
    return {"suite": "marks123", "per_suite": cmp_rep}


def run_selfpanel() -> dict:
    res = subprocess.run(
        [sys.executable, "-B", str(SCRIPTS / "fable_self105_runner.py"),
         "--run", "--out", str(OUTDIR / "selfpanel212")],
        capture_output=True, text=True, cwd=str(ROOT),
        env=dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1"))
    sys.stdout.write(res.stdout[-2000:])
    sys.stderr.write(res.stderr[-800:])
    out_path = OUTDIR / "selfpanel212" / "self105-results.json"
    rep = {"rc": res.returncode}
    try:
        got = json.loads(out_path.read_text(encoding="utf-8"))
        base = json.loads((ROOT / "artifacts" / "fable-self105-20260921"
                           / "self105-results.json").read_text(
                               encoding="utf-8"))
        gb, gg = _scrub(base), _scrub(got)
        rep["identical_to_sealed"] = (gb == gg)
        rep["wrong_got"] = got.get("WRONG", got.get("wrong", "?"))
        rep["wrong_base"] = base.get("WRONG", base.get("wrong", "?"))
    except (OSError, ValueError) as exc:
        rep["error"] = str(exc)
    print(f"selfpanel: {rep}", flush=True)
    return {"suite": "selfpanel105", **rep}


def main(argv=None) -> int:
    global OUTDIR
    ap = argparse.ArgumentParser(description="Exp 212 M3 suites")
    ap.add_argument("--only", default="all",
                    help="rt136|rt143|sessions|benchv3|marks|selfpanel|all")
    ap.add_argument("--suites", default="all",
                    help="marks-only subset, comma separated")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    t0 = time.time()
    if args.out:
        OUTDIR = Path(args.out)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    only = args.only
    out: dict = {}
    if only in ("all", "rt136"):
        out["rt136"] = run_rt136()
    if only in ("all", "rt143"):
        out["rt143"] = run_rt143()
    if only in ("all", "sessions"):
        out["sessions"] = run_sessions()
    if only in ("all", "benchv3"):
        out["benchv3"] = run_benchv3()
    if only in ("all", "marks"):
        out["marks"] = run_marks(args.suites)
    if only in ("all", "selfpanel"):
        out["selfpanel"] = run_selfpanel()
    out["seconds"] = round(time.time() - t0, 1)
    (OUTDIR / "suites212-summary.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False)[:200000],
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
