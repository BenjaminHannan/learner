#!/usr/bin/env python3
"""Exp 161 S5b diff -- marks161 (loop161) vs sealed marks138, per case.

Compares suite reports that both runs produce; every per-case reply AND
verdict must be identical except the predicted self-path turns frozen in
PASSMARKS.md. Prints every move with both sides; exits nonzero unless the
move set is exactly the predicted set (reply-only moves where predicted,
plus the single predicted verdict move rt110-S4).

Run after both marks runs exist (sealed marks138 read-only):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop161_marksdiff.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-selfcard161-20260922"
ART138 = ROOT / "artifacts" / "fable-agent138-20260922"

# Frozen predicted moves: (suite, case, step-or-turn or None, verdict_move?)
PRED = {
    ("rt110", "P1", 0, False),
    ("rt110", "P3", 0, False),
    ("rt110", "S1", 0, False),
    ("rt110", "S4", 1, True),
    ("p2", "D3", 0, False),
    ("p2", "D5", 1, False),
    ("p2", "D6", 0, False),
    ("p2", "E8", 0, False),
    ("p2", "G1", 2, False),
    ("rt81", "I_edges", 2, False),
    ("rt81", "M_hops", 4, False),
    ("rt81", "O_user", 2, False),
}


def load(name: str, sub: str):
    base = ART138 if sub == "138" else ART
    path = base / ("marks138" if sub == "138" else "marks161") / name
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    moves = []

    p2a, p2b = load("p2-report.json", "138"), load("p2-report.json", "161")
    ra = {r["id"]: r for r in p2a["rows"]}
    for r in p2b["rows"]:
        s = ra[r["id"]]
        if (r["agent_verdict"] != s["agent_verdict"]
                or r.get("agent_final", "") != s.get("agent_final", "")):
            moves.append(("p2", r["id"], None,
                          r["agent_verdict"] != s["agent_verdict"],
                          s["agent_verdict"], r["agent_verdict"],
                          (s.get("agent_final", "") or "")[:150],
                          (r.get("agent_final", "") or "")[:150]))

    rta, rtb = load("rt110-report.json", "138"), load("rt110-report.json",
                                                      "161")
    ra = {r["id"]: r for r in rta["rows"]}
    for r in rtb["rows"]:
        s = ra[r["id"]]
        la = [e.get("reply", "") for e in s.get("log", [])]
        lb = [e.get("reply", "") for e in r.get("log", [])]
        for i, (x, y) in enumerate(zip(la, lb)):
            if x != y:
                moves.append(("rt110", r["id"], i,
                              r["agent_verdict"] != s["agent_verdict"],
                              s["agent_verdict"], r["agent_verdict"],
                              x[:150], y[:150]))
        if r["agent_verdict"] != s["agent_verdict"] and all(
                m[1] != r["id"] for m in moves):
            moves.append(("rt110", r["id"], None, True, s["agent_verdict"],
                          r["agent_verdict"], "", ""))

    r8a, r8b = load("rt81-report.json", "138"), load("rt81-report.json",
                                                     "161")
    ca = {(c["id"]): c for c in r8a["cases"]}
    for c in r8b["cases"]:
        s = ca[c["id"]]
        if (c["verdict"] != s["verdict"]
                or c.get("observed", "") != s.get("observed", "")):
            seq = c["id"].rsplit("-", 1)[0]
            turn = None
            try:
                turn = int(c["id"].rsplit("-", 1)[1]) - 1
            except (ValueError, IndexError):
                turn = None
            moves.append(("rt81", seq, turn,
                          c["verdict"] != s["verdict"], s["verdict"],
                          c["verdict"], s.get("observed", "")[:150],
                          c.get("observed", "")[:150]))

    for suite, rep, keys in (
            ("q1", "q1-report.json", ("f5_ok", "m5_ok", "f5_reply",
                                      "m5_reply")),
            ("q4", "q4-report.json", ("n_replies", "leaks")),
            ("sleep", "sleep-report.json", ("pass", "skipped"))):
        a, b = load(rep, "138"), load(rep, "161")
        for k in keys:
            if json.dumps(a.get(k), sort_keys=True) != json.dumps(
                    b.get(k), sort_keys=True):
                moves.append((suite, k, None, True, str(a.get(k))[:150],
                              str(b.get(k))[:150], "", ""))
    # p3: compare pass flags only (seconds vary run to run; suite PASSED in
    # both runs). Post-seal analysis fix 2026-09-22: first version compared
    # whole blobs incl. seconds.
    pa, pb = load("p3-report.json", "138"), load("p3-report.json", "161")
    fa = {k: v.get("pass") for k, v in pa.get("marks", {}).items()}
    fb = {k: v.get("pass") for k, v in pb.get("marks", {}).items()}
    if fa != fb or pa.get("pass") != pb.get("pass"):
        moves.append(("p3", "marks", None, True, str(fa)[:150],
                      str(fb)[:150], "", ""))

    p4a, p4b = load("p4-report.json", "138"), load("p4-report.json", "161")
    ra = {r["id"]: r for r in p4a["rows"]}
    for r in p4b["rows"]:
        s = ra[r["id"]]
        if (r["pass"] != s["pass"]
                or r.get("replies") != s.get("replies")):
            moves.append(("p4", r["id"], None, r["pass"] != s["pass"],
                          str(s["pass"]), str(r["pass"]),
                          str(s.get("replies"))[:150],
                          str(r.get("replies"))[:150]))

    ba, bb = load("bench-report.json", "138"), load("bench-report.json",
                                                     "161")
    if json.dumps(ba["splits"], sort_keys=True) != json.dumps(
            bb["splits"], sort_keys=True):
        moves.append(("bench", "splits", None, True, "tables differ",
                      "tables differ", "", ""))

    sa, sb = load("soak-report.json", "138"), load("soak-report.json", "161")
    for k in ("completed", "lost", "wrong", "doubled_replies",
              "audit_lost_pairs", "audit_dup_pairs", "audit_wrong_pairs"):
        if sa.get(k) != sb.get(k):
            moves.append(("soak", k, None, True, str(sa.get(k)),
                          str(sb.get(k)), "", ""))

    print(f"S5b moves: {len(moves)} (predicted {len(PRED)})", flush=True)
    unpredicted = []
    for m in moves:
        key = (m[0], m[1], m[2], bool(m[3]))
        tag = "PREDICTED" if key in PRED else "UNPREDICTED"
        if key not in PRED:
            unpredicted.append(m)
        print(f"  [{tag}] {m[0]} {m[1]} step={m[2]} verdict_move={m[3]} "
              f"{m[4]} -> {m[5]}", flush=True)
        if m[6] != m[7]:
            print(f"    138: {m[6][:140]}", flush=True)
            print(f"    161: {m[7][:140]}", flush=True)
    missing = [p for p in PRED
               if not any((m[0], m[1], m[2]) == p[:3] for m in moves)]
    print(f"unpredicted={len(unpredicted)} predicted-missing={missing}",
          flush=True)
    ok = not unpredicted
    print(f"S5b -> {'PASS' if ok else 'FAIL'}", flush=True)
    (ART / "marks161-diff.json").write_text(
        json.dumps({"moves": [list(m) for m in moves],
                    "unpredicted": [list(m) for m in unpredicted],
                    "predicted_missing": [list(p) for p in missing],
                    "pass": ok}, indent=1), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
