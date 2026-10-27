#!/usr/bin/env python3
"""Exp 138g G2 compare -- marks138g per-case vs sealed marks138f.

Compares verdict + reply fields per suite, scrubbing volatile metadata
(seconds, tmp paths, agent/config paths, sleep SKIP reason filename,
l6 replied_before_kill). Prints every non-identical case. 0 exit when
all diffs are within the sealed predicted set (checked manually at
RESULTS time against PASSMARKS.md); this script only enumerates.

Run (Mac CPU, offline; read-only, no agent run):
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138g_compareg2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
G = ROOT / "artifacts" / "fable-agent138g-20260922" / "marks138g"
F = ROOT / "artifacts" / "fable-agent138f-20260922" / "marks138f"

SCRUB_KEYS = {"seconds", "wall_seconds", "elapsed", "tmp", "workdir",
              "work_dir", "out", "outdir", "config", "agent",
              "agent_module", "replied_before_kill", "killed",
              "timestamp", "started", "ended", "pid", "hostname",
              "event_id", "hash", "chain_hash", "daemon_workdir"}


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


def load_report(name: str):
    g = json.loads((G / name).read_text(encoding="utf-8"))
    f = json.loads((F / name).read_text(encoding="utf-8"))
    return g, f


def case_lists(rep: dict) -> dict:
    """Find per-case lists inside a suite report."""
    out = {}
    if isinstance(rep, dict):
        for k, v in rep.items():
            if isinstance(v, list) and v and isinstance(v[0], dict) and (
                    "id" in v[0] or "turn" in v[0] or "case" in v[0]):
                out[k] = v
            elif isinstance(v, dict):
                for k2, v2 in case_lists(v).items():
                    out[f"{k}.{k2}"] = v2
    return out


def verdict_of(row: dict):
    for k in ("verdict", "status", "result", "mark", "pass"):
        if k in row:
            return row[k]
    return None


def reply_of(row: dict):
    for k in ("agent_final", "reply", "observed", "agent_reply",
              "final", "text_out", "loop96_reply"):
        if k in row and isinstance(row[k], str):
            return row[k]
    return None


def main() -> int:
    files = ["p2-report.json", "p4-report.json", "rt81-report.json",
             "rt110-report.json", "q1-report.json", "q4-report.json",
             "sleep-report.json", "soak-report.json", "bench-report.json",
             "p3-report.json", "fable_marks123_summary.json"]
    total_moves = 0
    for name in files:
        gp, fp = G / name, F / name
        if not gp.exists() or not fp.exists():
            print(f"{name}: MISSING on one arm", flush=True)
            continue
        g, f = load_report(name)
        gs, fs = scrub(g), scrub(f)
        if gs == fs:
            print(f"{name}: identical (scrubbed)", flush=True)
            continue
        # per-case diff
        gl, fl = case_lists(g), case_lists(f)
        shown = 0
        keys = sorted(set(gl) | set(fl))
        for key in keys:
            gv = {str(r.get("id", r.get("turn", i))): r
                  for i, r in enumerate(gl.get(key, []))}
            fv = {str(r.get("id", r.get("turn", i))): r
                  for i, r in enumerate(fl.get(key, []))}
            for cid in sorted(set(gv) | set(fv)):
                gr, fr = gv.get(cid), fv.get(cid)
                if gr is None or fr is None:
                    print(f"{name} {key} {cid}: PRESENT on one arm only",
                          flush=True)
                    shown += 1
                    continue
                if scrub(gr) == scrub(fr):
                    continue
                gv_v, fv_v = verdict_of(gr), verdict_of(fr)
                gr_r, fr_r = reply_of(gr), reply_of(fr)
                vm = "VERDICT" if gv_v != fv_v else "reply-only"
                print(f"{name} {key} {cid}: {vm} "
                      f"f={fv_v!r} g={gv_v!r}", flush=True)
                if gr_r != fr_r and (gr_r is not None or fr_r is not None):
                    print(f"    f-reply: {str(fr_r)[:200]!r}",
                          flush=True)
                    print(f"    g-reply: {str(gr_r)[:200]!r}",
                          flush=True)
                shown += 1
                total_moves += 1
        if shown == 0:
            print(f"{name}: summary-only diff (volatile metadata)",
                  flush=True)
    print(f"TOTAL per-case moves: {total_moves}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
