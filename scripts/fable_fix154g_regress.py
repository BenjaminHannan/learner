#!/usr/bin/env python3
"""Experiment 154g -- regression runner (bench G1 + marks G2, registered).

Same pattern as scripts/fable_fix154e_regress.py with the daemon class
swapped to Loop154gDaemon. Bench compares against the FROZEN loop154e
rows in artifacts/fable-lang154e-20260922/; marks123 compares per-case
against frozen marks154e (scrubbing only volatile seconds/timings and
the predicted sleep-SKIP agent filename). Outputs under
artifacts/fable-nocorrect154g-20260922/.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench121_run as B  # noqa: E402 (run_item/scorer, read-only)
import fable_loop154g_agent as L154g  # noqa: E402 (agent under test)

ART = ROOT / "artifacts" / "fable-nocorrect154g-20260922"
ART154E = ROOT / "artifacts" / "fable-lang154e-20260922"
AGENT = str(SCRIPTS / "fable_loop154g_agent.py")
CONFIG = str(ART / "loop154g-config.json")

SPLITS_3 = (
    ("new_121_4hop", B.DATA_NEW,
     "fable_bench121_loop154e_new_121_4hop_rows.jsonl"),
    ("old_s2fresh_4hop", B.DATA_OLD,
     "fable_bench121_loop154e_old_s2fresh_4hop_rows.jsonl"),
    ("edit200", ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl",
     "fable_bench121_loop154e_edit200_rows.jsonl"),
)
SPLIT_132 = (("bench132_4hop",
              ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl",
              "fable_bench121_loop154e_bench132_4hop_rows.jsonl"))


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(
        encoding="utf-8").splitlines() if line.strip()]


def run_bench(only: str, outdir: Path) -> dict:
    B.Loop121Daemon = L154g.Loop154gDaemon
    cfg = json.loads(Path(CONFIG).read_text(encoding="utf-8"))
    cfg["sleep_threshold"] = 100000
    want = only.split(",")
    splits = list(SPLITS_3) + [SPLIT_132]
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = outdir / "scratch-bench121-loop154g"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    summary: dict = {"seconds": 0.0, "agent": "loop154g", "splits": {}}
    diffs: list[dict] = []
    for stag, path, sealed_name in splits:
        items = load_rows(Path(str(path)))
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (outdir / f"fable_bench121_loop154g_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        frozen = {r.get("id", i): r for i, r in
                  enumerate(load_rows(ART154E / sealed_name))}
        new_wrong, moves = 0, []
        for i, row in enumerate(rows):
            old = frozen.get(row.get("id", i), {})
            if row.get("verdict") != old.get("verdict") or \
                    row.get("reply", "") != old.get("reply", ""):
                moves.append({"id": row.get("id", i),
                              "was": old.get("verdict"),
                              "now": row.get("verdict"),
                              "was_reply": (old.get("reply", "") or "")[:160],
                              "now_reply": (row.get("reply", "") or "")[:160]})
            if row.get("verdict") == "wrong" and old.get("verdict") != "wrong":
                new_wrong += 1
        summary["splits"][stag] = {"n": len(rows), "new_wrong": new_wrong,
                                   "moves": len(moves)}
        diffs.extend([dict(d, split=stag) for d in moves])
    summary["seconds"] = round(time.time() - t0, 1)
    summary["new_wrong_total"] = sum(
        v["new_wrong"] for v in summary["splits"].values())
    (outdir / "bench154g_diff.json").write_text(
        json.dumps({"summary": summary, "moves": diffs}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    return summary


VOLATILE_KEYS = {"seconds", "elapsed", "elapsed_s", "ms", "duration",
                 "timings", "timestamp", "started", "ended"}


def scrub(obj):
    """Drop volatile timing keys; normalise the predicted agent filename
    and tmp workdir segments so only real moves surface."""
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()
                if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    if isinstance(obj, str):
        s = obj.replace("fable_loop154e_agent.py", "AGENT.py")
        s = s.replace("fable_loop154g_agent.py", "AGENT.py")
        s = re.sub(r"[A-Za-z0-9_./-]*tmp[A-Za-z0-9_./-]*", "TMP", s)
        return s
    return obj


def walk_diff(old, new, path: str, moves: list) -> None:
    if old == new:
        return
    if isinstance(old, dict) and isinstance(new, dict):
        for k in sorted(set(old) | set(new)):
            walk_diff(old.get(k, "<ABSENT>"), new.get(k, "<ABSENT>"),
                      f"{path}.{k}", moves)
        return
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            moves.append({"path": path, "old_len": len(old),
                          "new_len": len(new)})
            return
        for i, (o, n) in enumerate(zip(old, new)):
            walk_diff(o, n, f"{path}[{i}]", moves)
        return
    moves.append({"path": path, "was": str(old)[:160],
                  "now": str(new)[:160]})


def verify_rt110_statuses_race(new_dir: Path, frozen_dir: Path,
                               moves: list[dict]) -> tuple[list[dict],
                                                           list[dict]]:
    """Split rt110 `.statuses` leaf diffs into race-confirmed (volatile)
    vs real. The harness reads daemon.log.jsonl the moment the reply
    lands in done/ -- but process_file moves the file to done/ BEFORE
    appending the turn event, so a fast poll observes []. The daemon log
    written moments later always holds the full records; when it matches
    the frozen statuses, the diff is proven harness timing, not agent
    behaviour (verdicts, replies and fact_writes are identical either
    way). Returns (confirmed_race, rest)."""
    import glob as _glob
    race, rest = [], []
    frozen = {r["id"]: r for r in
              json.loads((frozen_dir / "rt110-report.json").read_text(
                  encoding="utf-8"))["rows"]}
    new = {r["id"]: r for r in
           json.loads((new_dir / "rt110-report.json").read_text(
               encoding="utf-8"))["rows"]}
    for m in moves:
        if "rt110-report.json" not in m.get("path", "") or \
                ".statuses" not in m.get("path", ""):
            rest.append(m)
            continue
        mm = re.search(r"rows\[(\d+)\]", m["path"])
        if mm is None:
            rest.append(m)
            continue
        idx = int(mm.group(1))
        frows = json.loads((frozen_dir / "rt110-report.json").read_text(
            encoding="utf-8"))["rows"]
        nrows = json.loads((new_dir / "rt110-report.json").read_text(
            encoding="utf-8"))["rows"]
        if idx >= len(frows) or idx >= len(nrows):
            rest.append(m)
            continue
        case_id, entry = frows[idx]["id"], None
        nlog = nrows[idx].get("log", [])
        fmatch = re.search(r"log\[(\d+)\]", m["path"])
        if fmatch is None:
            rest.append(m)
            continue
        li = int(fmatch.group(1))
        if li >= len(nlog):
            rest.append(m)
            continue
        fname = nlog[li].get("file")
        want = frows[idx]["log"][li].get("statuses")
        got = None
        for workdir in _glob.glob(str(new_dir / "rt110-tmp"
                                      / f"{case_id}_*")):
            logp = Path(workdir) / "daemon.log.jsonl"
            if not logp.exists():
                continue
            for line in logp.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("event") == "turn" and \
                        rec.get("file") == fname:
                    got = [r.get("status", r.get("kind", "?"))
                           for r in rec.get("records", [])]
        if got is not None and got == want:
            race.append({**m, "race_confirmed": True,
                         "daemon_log_statuses": got})
        else:
            rest.append({**m, "race_confirmed": False,
                         "daemon_log_statuses": got})
    return race, rest


def compare_marks(outdir: Path) -> dict:
    frozen_dir = ART154E / "marks154e"
    new_dir = outdir / "marks154g"
    reports = sorted(p.name for p in frozen_dir.glob("*-report.json"))
    per_report: dict = {}
    all_moves: list[dict] = []
    for name in reports:
        fpath, npath = frozen_dir / name, new_dir / name
        if not npath.exists():
            per_report[name] = {"status": "MISSING-IN-NEW"}
            all_moves.append({"report": name, "issue": "missing"})
            continue
        old = scrub(json.loads(fpath.read_text(encoding="utf-8")))
        new = scrub(json.loads(npath.read_text(encoding="utf-8")))
        moves: list[dict] = []
        walk_diff(old, new, name, moves)
        per_report[name] = {"status": "IDENTICAL" if not moves
                            else f"{len(moves)}-DIFFS"}
        all_moves.extend(moves)
    # Bench reply texts: every reply byte-identical (volatile-free zone).
    bench_moves = 0
    for suffix in ("new_121_4hop", "old_s2fresh_4hop", "edit200",
                   "bench132_4hop"):
        cand_old = sorted(frozen_dir.glob(f"bench-rows-*{suffix}*.jsonl"))
        cand_new = sorted(new_dir.glob(f"bench-rows-*{suffix}*.jsonl"))
        if cand_old and cand_new:
            ro = {r.get("id"): r.get("reply", "") for r in
                  load_rows(cand_old[0])}
            rn = {r.get("id"): r.get("reply", "") for r in
                  load_rows(cand_new[0])}
            for rid, reply in rn.items():
                if ro.get(rid) != reply:
                    bench_moves += 1
                    all_moves.append({"report": f"bench-rows-{suffix}",
                                      "id": rid})
    summary = {"reports": per_report, "n_diffs": len(all_moves),
               "bench_reply_moves": bench_moves}
    race, rest = verify_rt110_statuses_race(outdir / "marks154g",
                                            frozen_dir, all_moves)
    summary["rt110_statuses_race_confirmed"] = race
    summary["real_moves"] = rest
    summary["verdict"] = "PASS" if not rest and not bench_moves else "FAIL"
    (outdir / "marks154g_diff.json").write_text(
        json.dumps({"summary": summary, "moves": rest[:200],
                    "race": race}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return summary


def run_marks(suites: str, outdir: Path, workers: int) -> dict:
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    cmd = [sys.executable, "-B", str(SCRIPTS / "fable_marks123_all.py"),
           "--agent", AGENT, "--config", CONFIG,
           "--out", str(outdir / "marks154g"),
           "--suites", suites, "--workers", str(workers)]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return {"rc": proc.returncode, "seconds": round(time.time() - t0, 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 154g regression runner")
    ap.add_argument("--bench", action="store_true")
    ap.add_argument("--marks", default=None,
                    help="comma suites for marks123 (e.g. p2,rt110,rt81)")
    ap.add_argument("--compare-marks", action="store_true")
    ap.add_argument("--only", default="all")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=str(ART))
    args = ap.parse_args(argv)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    rc = 0
    if args.bench:
        summary = run_bench(args.only, outdir)
        print(json.dumps({"bench154g": summary}, indent=1))
        rc = rc or int(summary["new_wrong_total"] > 0)
    if args.marks:
        rep = run_marks(args.marks, outdir, args.workers)
        print(json.dumps({"marks154g": rep}, indent=1))
        rc = rc or int(rep["rc"] != 0)
    if args.compare_marks:
        summary = compare_marks(outdir)
        rc = rc or int(summary["verdict"] != "PASS")
    return rc


if __name__ == "__main__":
    sys.exit(main())
