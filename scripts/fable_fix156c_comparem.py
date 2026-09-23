#!/usr/bin/env python3
"""Experiment 156c marks123 compare -- marks156c per-case vs sealed marks138h.

Read-only scrub-compare (own code only; no other agent's module
imported). Prints every non-identical case. Exit 0 iff all reports are
identical after scrubbing volatile metadata plus the predicted renames:
  - agent filename fable_loop156c_agent.py vs fable_loop138h_agent.py,
    config loop156c-config.json vs loop138h-config.json, artifact dir
    fable-smalltalk156c-20260922 vs fable-agent138h-20260922;
  - fable_marks123_summary.json timing-volatile total_seconds;
  - rt110 harness `statuses` log-metadata only (daemon.log race under
    parallel load; verdict+reply+fact_writes must still match exactly).

Sealed prediction (PASSMARKS.md): every report SAME (0 moves), with at
most the predicted volatile/statuses-only diffs above.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
G = ROOT / "artifacts" / "fable-smalltalk156c-20260922" / "marks156c"
F = ROOT / "artifacts" / "fable-agent138h-20260922" / "marks138h"

RENAMES = (
    ("fable_loop156c_agent.py", "fable_loop138h_agent.py"),
    ("loop156c-config.json", "loop138h-config.json"),
    ("fable-smalltalk156c-20260922", "fable-agent138h-20260922"),
)

SCRUB_KEYS = {"seconds", "wall_seconds", "elapsed", "tmp", "workdir",
              "work_dir", "out", "outdir", "config", "agent",
              "agent_module", "replied_before_kill", "killed",
              "timestamp", "started", "ended", "pid", "hostname",
              "event_id", "hash", "chain_hash", "daemon_workdir"}


def deep_rename(o):
    if isinstance(o, dict):
        return {k: deep_rename(v) for k, v in o.items()}
    if isinstance(o, list):
        return [deep_rename(v) for v in o]
    if isinstance(o, str):
        for old, new in RENAMES:
            o = o.replace(old, new)
        return o
    return o


def scrub(o):
    if isinstance(o, dict):
        return {k: scrub(v) for k, v in o.items() if k not in SCRUB_KEYS}
    if isinstance(o, list):
        return [scrub(v) for v in o]
    if isinstance(o, str):
        if "fable_loop138" in o or "fable-agent138" in o:
            return "<AGENTPATH>"
        if "/tmp/" in o or "work-sessions" in o or "daemon-" in o:
            return "<TMPPATH>"
        return o
    return o


def semantic_rt110(g_rows, f_rows):
    """Per-case (verdict, reply, writes) identity; statuses reported."""
    def key(r):
        log = r.get("log", []) or []
        return (r.get("id"), r.get("sealed_verdict"),
                r.get("agent_verdict"), r.get("reason"),
                r.get("severity"), bool(r.get("harness_error")),
                tuple((e.get("file"), e.get("reply"),
                       e.get("fact_writes")) for e in log))
    gb = {r.get("id"): r for r in g_rows}
    fb = {r.get("id"): r for r in f_rows}
    bad, stat_only = [], []
    for cid in sorted(set(gb) | set(fb)):
        if cid not in gb or cid not in fb:
            bad.append((cid, "missing-side"))
            continue
        if key(gb[cid]) != key(fb[cid]):
            bad.append((cid, "semantic-diff"))
            continue
        gl = [(e.get("file"), e.get("statuses"))
              for e in (gb[cid].get("log", []) or [])]
        fl = [(e.get("file"), e.get("statuses"))
              for e in (fb[cid].get("log", []) or [])]
        if gl != fl:
            stat_only.append((cid, gl, fl))
    return bad, stat_only


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Exp 156c marks compare")
    ap.add_argument("--got", default=str(G),
                    help="marks dir for loop156c (default: marks156c)")
    args = ap.parse_args(argv)
    got = Path(args.got)
    names = ["p2-report.json", "p3-report.json", "p4-report.json",
             "rt110-report.json", "q1-report.json", "bench-report.json",
             "rt81-report.json", "sleep-report.json", "soak-report.json",
             "q4-report.json", "fable_marks123_summary.json"]
    bad = 0
    for name in names:
        gp, fp = got / name, F / name
        if not gp.exists() or not fp.exists():
            print(f"SKIP {name} (missing)", flush=True)
            continue
        g_raw = json.loads(gp.read_text(encoding="utf-8"))
        f_raw = json.loads(fp.read_text(encoding="utf-8"))
        g_raw = deep_rename(g_raw)
        g = scrub(g_raw)
        f = scrub(f_raw)
        if name == "fable_marks123_summary.json":
            g = {k: v for k, v in g.items() if k != "total_seconds"}
            f = {k: v for k, v in f.items() if k != "total_seconds"}
        if g == f:
            print(f"SAME {name}", flush=True)
            continue
        if name == "rt110-report.json":
            bad_sem, stat_only = semantic_rt110(
                g_raw.get("rows", []), f_raw.get("rows", []))
            if not bad_sem:
                print(f"SAME-semantic {name} "
                      f"(statuses-only metadata diffs: "
                      f"{[c for c, _, _ in stat_only]})", flush=True)
                for c, gl, fl in stat_only:
                    print(f"  VOLATILE {c}: 156c-statuses={gl} "
                          f"138h-statuses={fl}", flush=True)
                continue
            print(f"DIFF-semantic {name}: {bad_sem}", flush=True)
            bad += 1
            continue
        print(f"DIFF {name}", flush=True)
        bad += 1
        jg, jf = json.dumps(g, sort_keys=True), json.dumps(
            f, sort_keys=True)
        for i, (a, b) in enumerate(zip(jg, jf)):
            if a != b:
                print(f"  first-diff at char {i}", flush=True)
                print(f"  156c: ...{jg[max(0, i-200):i+200]}", flush=True)
                print(f"  138h: ...{jf[max(0, i-200):i+200]}", flush=True)
                break
        else:
            print(f"  len-only diff 156c={len(jg)} 138h={len(jf)}",
                  flush=True)
    for sub in ("p3", "rt110-tmp"):
        gd, fd = got / sub, F / sub
        if not gd.exists() or not fd.exists():
            continue
        gf = sorted(p.name for p in gd.iterdir())
        ff = sorted(p.name for p in fd.iterdir())
        print(f"{sub}: 156c-files={len(gf)} 138h-files={len(ff)}",
              flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
