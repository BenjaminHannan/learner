#!/usr/bin/env python3
"""Exp 218 SUITE-DIFF CLASSES + ANY BASE (harness only; no agent change).

Wraps the shared tool scripts/fable_suitediff.py (exp 214) read-only and
reuses its runners. THE ONE CHANGE is (a) the move classes and (b) the
base lookup. scripts/fable_suitediff.py is never edited; this module
imports it and only patches the classifier attribute at runtime.

Move classes, checked in this order for every moved case:
  1. "new WRONG-WRITE"   (as 214)
  2. "new WRONG"          (as 214)
  3. "new junk write"     (as 214, both clauses)
  4. "lost OK"            (base verdict OK, new verdict not OK)
  5. "fixed"              (base verdict not OK, new verdict OK)
  6. "write change"       (stored triples or fact-write count differ,
                           verdicts otherwise not covered above)
  7. "reply-only move"    ONLY when verdict and stored triples are both
                           identical and only the reply text changed.

Summary line per suite lists the count of every class, plus one final
line "GATE: clean" iff new WRONG + new WRONG-WRITE + new junk write +
lost OK = 0 over all suites run, else
"GATE: NOT clean (<counts>)".

Base lookup: --base 138h|138i (same sealed dirs 214 uses) or
--base-dir <any sealed agent artifact folder>. Rows files are found by
the same filename search 214 uses. If a suite's rows file is missing in
that folder, the suite is reported SKIPPED (never silently passed).

Run (Mac CPU, offline, one suite at a time; only AFTER PASSMARKS sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_suitediff218.py \\
    --agent scripts/fable_loop138i_agent.py \\
    --config artifacts/fable-agent138i-20260922/loop138i-config.json \\
    --base 138i --out <dir> [--only rt136|rt143|sessions152|bench|marks123|all]
  ... or --base-dir artifacts/fable-agent138i-20260922 instead of --base.

Classifier self-check (mark C1):
  python -B scripts/fable_suitediff218.py --check-table <pairs.json>
"""

from __future__ import annotations

import argparse
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

import fable_suitediff as S214  # noqa: E402 (wrapped, read-only; never edited)

CLASSES218 = ("new WRONG-WRITE", "new WRONG", "new junk write", "lost OK",
              "fixed", "write change", "reply-only move")

GATE_CLASSES = ("new WRONG", "new WRONG-WRITE", "new junk write", "lost OK")


def classify218(base: dict, new: dict, suite: str = "") -> dict:
    """Class a moved case with the exp-218 classes (checked in order)."""
    bv, nv = base.get("verdict"), new.get("verdict")
    # 1-3: exactly as 214.
    if S214.is_new_wrong(bv, nv) and nv == "WRONG-WRITE":
        return {"class": "new WRONG-WRITE",
                "detail": f"{bv} -> {nv}"}
    if S214.is_new_wrong(bv, nv):
        return {"class": "new WRONG",
                "detail": f"{bv} -> {nv}"}
    bw = base.get("stored", base.get("fact_writes", base.get("writes", [])))
    nw = new.get("stored", new.get("fact_writes", new.get("writes", [])))
    if (nw not in (None, [], 0)) and (nw != bw) and not bw:
        return {"class": "new junk write",
                "detail": f"writes {bw!r} -> {nw!r}"[:200]}
    if (nw != bw) and (bv in S214.WRONGish or nv in S214.WRONGish):
        return {"class": "new junk write",
                "detail": f"writes {bw!r} -> {nw!r}"[:200]}
    # 4-5: verdict OK transitions.
    if bv == "OK" and nv != "OK":
        return {"class": "lost OK",
                "detail": f"{bv} -> {nv}"}
    if bv != "OK" and nv == "OK":
        return {"class": "fixed",
                "detail": f"{bv} -> {nv}"}
    # 6: stored triples or fact-write count differ.
    bfw = base.get("fact_writes", None)
    nfw = new.get("fact_writes", None)
    fw_differs = ((bfw is not None or nfw is not None)
                  and (bfw or 0) != (nfw or 0))
    if (bw != nw) or fw_differs:
        return {"class": "write change",
                "detail": f"writes {bw!r} -> {nw!r}, "
                          f"fact_writes {bfw!r} -> {nfw!r}"[:200]}
    # 7: verdict and stored triples identical; only the reply moved.
    return {"class": "reply-only move",
            "detail": f"verdict {bv}->{nv}, stored identical, "
                      f"reply {str(base.get('reply', ''))[:60]!r} -> "
                      f"{str(new.get('reply', ''))[:60]!r}"[:200]}


def summary_line218(suite: str, moves: list, seconds: float) -> str:
    classes = Counter(m["class"] for m in moves)
    parts = ", ".join(f"{c}={int(classes.get(c, 0))}" for c in CLASSES218)
    extra = sorted(k for k in classes if k not in CLASSES218)
    if extra:
        parts += ", " + ", ".join(f"{k}={int(classes[k])}" for k in extra)
    return (f"{suite}: n_moves={len(moves)} ({parts}) "
            f"seconds={seconds}")


def gate_line(reps: dict) -> str:
    totals = Counter()
    for rep in reps.values():
        totals.update(Counter(rep.get("class_counts", {})))
    n = sum(int(totals.get(c, 0)) for c in GATE_CLASSES)
    if n == 0:
        return "GATE: clean"
    counts = ", ".join(f"{c} {int(totals.get(c, 0))}" for c in GATE_CLASSES)
    return f"GATE: NOT clean ({counts})"


def check_table(path: str) -> int:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    pairs = obj if isinstance(obj, list) else obj.get("pairs", obj)
    n_ok, n_all = 0, 0
    for p in pairs:
        n_all += 1
        got = classify218(p["base"], p["new"],
                          p.get("suite", ""))["class"]
        want = p["expected"]
        mark = "OK" if got == want else "MISMATCH"
        if got == want:
            n_ok += 1
        print(f"{p.get('id', n_all)}: want={want} got={got} {mark}",
              flush=True)
    print(f"classifier table: {n_ok}/{n_all} match", flush=True)
    return 0 if n_ok == n_all and n_all > 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 218 suite-diff v2")
    ap.add_argument("--agent", default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--base", default=None, choices=["138h", "138i"])
    ap.add_argument("--base-dir", default=None,
                    help="any sealed agent artifact folder")
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default="all",
                    help="comma list of rt136,rt143,sessions152,bench,"
                         "marks123 (or all)")
    ap.add_argument("--bench-only", default="all")
    ap.add_argument("--check-table", default=None,
                    help="classify hand-made (base,new) pairs and exit")
    args = ap.parse_args(argv)
    if args.check_table:
        return check_table(args.check_table)
    if not args.agent or not args.config or not args.out:
        ap.error("--agent, --config and --out are required "
                 "(unless --check-table)")
    if bool(args.base) == bool(args.base_dir):
        ap.error("pass exactly one of --base <138h|138i> or --base-dir <dir>")
    if args.base_dir:
        base_dir = Path(args.base_dir)
        if not base_dir.is_dir():
            print(f"base dir missing: {base_dir}", flush=True)
            return 2
        base_label = str(base_dir)
    else:
        base_dir = S214.BASE_DIRS[args.base]
        base_label = args.base
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="suitediff218-work-"))
    # THE ONE CHANGE, part 1: 218 move classes for every reused runner.
    S214.classify_reply_move = classify218  # type: ignore[method-assign]
    _, daemon_cls, _, _ = S214.load_agent(args.agent)
    base_cfg = S214.load_base_cfg(args.config)
    want = S214.SUITES if args.only == "all" else args.only.split(",")
    for s in want:
        if s not in S214.SUITES:
            print(f"unknown suite {s}", flush=True)
            return 2
    t0 = time.time()
    reps: dict = {}
    skipped: dict = {}
    for s in want:
        t1 = time.time()
        try:
            if s == "rt136":
                reps[s] = S214.run_rt136(out, work, daemon_cls, base_cfg,
                                         base_dir)
            elif s == "rt143":
                reps[s] = S214.run_rt143(out, work, daemon_cls, base_cfg,
                                         base_dir)
            elif s == "sessions152":
                reps[s] = S214.run_sessions(out, work, daemon_cls, base_cfg,
                                            base_dir)
            elif s == "bench":
                reps[s] = S214.run_bench(out, work, daemon_cls, base_cfg,
                                         base_dir, args.bench_only)
            elif s == "marks123":
                reps[s] = S214.run_marks123(out, args.agent, args.config,
                                            base_dir)
        except RuntimeError as e:
            if "no sealed" in str(e):
                skipped[s] = str(e)
                print(f"{s}: SKIPPED ({e})", flush=True)
                continue
            raise
        # Re-stamp the per-suite summary line in the 218 format (every
        # class listed) now that the reused runner classified with 218.
        rep = reps[s]
        secs = round(time.time() - t1, 1)
        line = summary_line218(s, rep.get("moves", []), secs)
        print(line, flush=True)
        rep["summary_line"] = line
        rep["seconds"] = secs
        (out / f"{s}-diff.json").write_text(
            json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"done {s} in {secs}s", flush=True)
    shutil.rmtree(work, ignore_errors=True)
    gl = gate_line(reps)
    print(gl, flush=True)
    summary = {"agent": args.agent, "config": args.config,
               "base": base_label, "suites": want,
               "summary_lines": [reps[s]["summary_line"] for s in reps],
               "skipped": skipped, "gate": gl,
               "seconds": round(time.time() - t0, 1)}
    (out / "SUITEDIFF218-SUMMARY.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    for line in summary["summary_lines"]:
        print(line, flush=True)
    for s, why in skipped.items():
        print(f"{s}: SKIPPED ({why})", flush=True)
    print(gl, flush=True)
    print(f"TOTAL seconds={summary['seconds']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
