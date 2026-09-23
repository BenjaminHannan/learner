#!/usr/bin/env python3
"""Exp 158c G2 driver -- marks123 suites through loop158c vs sealed marks158b.

Runs scripts/fable_marks123_all.py suite-by-suite (stock code, sequential
subprocesses) with --agent scripts/fable_loop158c_agent.py into
artifacts/fable-whcity158c-20260922/marks158c, then compares per-case
against artifacts/fable-whrel158b-20260922/marks158b:
  p2/p4/rt110 rows by id (verdict + reply), p3 per-mark pass, q1 flags +
  replies, bench rows verdict + reply, rt81 cases verdict + observed,
  sleep skip-reason (agent filename differs: predicted), soak counters,
  q4 leaks.
Bar: per-case identical except the predicted sleep-reason filename line;
0 verdict moves. rt110 note: a harness-error flake under load is the known
mailbox race -- re-run once in the open and report both.
Outputs into artifacts/fable-whcity158c-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix158c_marks.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-whcity158c-20260922"
BASE = ROOT / "artifacts" / "fable-whrel158b-20260922" / "marks158b"
OUT = ART / "marks158c"

SUITES = ["p2", "p3", "p4", "rt110", "q1", "bench", "rt81", "sleep", "soak"]


def run_suites() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    for s in SUITES:
        cmd = [sys.executable, "-B", str(SCRIPTS / "fable_marks123_all.py"),
               "--agent", "scripts/fable_loop158c_agent.py",
               "--config",
               "artifacts/fable-whcity158c-20260922/loop158c-config.json",
               "--out", str(OUT), "--suite", s]
        p = subprocess.run(cmd, capture_output=True, text=True, env=env,
                           cwd=str(ROOT))
        sys.stdout.write(p.stdout)
        sys.stderr.write(p.stderr)
        if p.returncode not in (0, 1):
            print(f"G2 {s}: driver rc={p.returncode}", flush=True)
    # Q4 over collected replies (same rule as the stock --suite all flow).
    sys.path.insert(0, str(SCRIPTS))
    import fable_marks123_all as M123  # noqa: E402
    q4 = M123.suite_q4(OUT, M123.collect_replies(OUT))
    print(f"G2 q4: leaks={q4.get('leaks', [])}", flush=True)


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def load_rows_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8")
            .splitlines() if l.strip()]


def filename_only_diff(a: str, b: str) -> bool:
    """True if the only difference is the agent script filename."""
    na = str(a).replace("fable_loop158c_agent.py", "AGENT")
    nb = (str(b).replace("fable_loop158b_agent.py", "AGENT")
          .replace("fable_loop138b_agent.py", "AGENT"))
    return na == nb


def compare() -> dict:
    moves: list[dict] = []
    allowed: list[dict] = []

    def note(suite: str, cid: str, field: str, b, g):
        if field in ("reply", "observed", "agent_final", "reason",
                     "replies") and filename_only_diff(g, b):
            allowed.append({"suite": suite, "id": cid, "field": field})
        else:
            moves.append({"suite": suite, "id": cid, "field": field,
                          "loop158b": str(b)[:120],
                          "loop158c": str(g)[:120]})

    p2b, p2g = load(BASE / "p2-report.json"), load(OUT / "p2-report.json")
    for r in p2g["rows"]:
        b = next(x for x in p2b["rows"] if x["id"] == r["id"])
        if r["agent_verdict"] != b["agent_verdict"]:
            note("p2", r["id"], "agent_verdict", b["agent_verdict"],
                 r["agent_verdict"])
        if r["agent_final"] != b["agent_final"]:
            note("p2", r["id"], "agent_final", b["agent_final"],
                 r["agent_final"])

    p3b, p3g = load(BASE / "p3-report.json"), load(OUT / "p3-report.json")
    if p3g.get("selected") != p3b.get("selected"):
        moves.append({"suite": "p3", "id": "*", "field": "selected",
                      "loop158b": str(p3b.get("selected")),
                      "loop158c": str(p3g.get("selected"))})
    for m, g in p3g.get("marks", {}).items():
        if g.get("pass") != p3b.get("marks", {}).get(m, {}).get("pass"):
            moves.append({"suite": "p3", "id": m, "field": "pass",
                          "loop158b": p3b["marks"][m]["pass"],
                          "loop158c": g["pass"]})

    p4b, p4g = load(BASE / "p4-report.json"), load(OUT / "p4-report.json")
    for r in p4g["rows"]:
        b = next(x for x in p4b["rows"] if x["id"] == r["id"])
        for f in ("pass", "false_refusal", "replies", "stored"):
            if r.get(f) != b.get(f):
                note("p4", r["id"], f, b.get(f), r.get(f))

    rtb, rtg = load(BASE / "rt110-report.json"), load(OUT / "rt110-report.json")
    for r in rtg["rows"]:
        b = next(x for x in rtb["rows"] if x["id"] == r["id"])
        if r["agent_verdict"] != b["agent_verdict"]:
            note("rt110", r["id"], "agent_verdict", b["agent_verdict"],
                 r["agent_verdict"])
        if r.get("harness_error") != b.get("harness_error"):
            moves.append({"suite": "rt110", "id": r["id"],
                          "field": "harness_error",
                          "loop158b": b.get("harness_error"),
                          "loop158c": r.get("harness_error")})

    q1b, q1g = load(BASE / "q1-report.json"), load(OUT / "q1-report.json")
    for f in ("f5_ok", "m5_ok", "f5_reply", "m5_reply"):
        if q1g.get(f) != q1b.get(f):
            note("q1", "*", f, q1b.get(f), q1g.get(f))

    for tag in ("fable_edit_200", "s2fresh_4hop"):
        bb = {r["id"]: r for r in
              load_rows_jsonl(BASE / f"bench-rows-{tag}.jsonl")}
        gg = load_rows_jsonl(OUT / f"bench-rows-{tag}.jsonl")
        for r in gg:
            b = bb.get(r["id"])
            if b is None:
                continue
            if r["verdict"] != b["verdict"]:
                note("bench", f"{tag}/{r['id']}", "verdict",
                     b["verdict"], r["verdict"])
            if r.get("reply") != b.get("reply"):
                note("bench", f"{tag}/{r['id']}", "reply",
                     b.get("reply"), r.get("reply"))

    r8b, r8g = load(BASE / "rt81-report.json"), load(OUT / "rt81-report.json")
    b8 = {c["id"]: c for c in r8b["cases"]}
    for c in r8g["cases"]:
        b = b8.get(c["id"])
        if b is None:
            continue
        if c["verdict"] != b["verdict"]:
            note("rt81", c["id"], "verdict", b["verdict"], c["verdict"])
        if c.get("observed") != b.get("observed"):
            note("rt81", c["id"], "observed", b.get("observed"),
                 c.get("observed"))

    slb, slg = load(BASE / "sleep-report.json"), load(OUT / "sleep-report.json")
    if slg.get("skipped") != slb.get("skipped") or \
            slg.get("pass") != slb.get("pass"):
        moves.append({"suite": "sleep", "id": "*", "field": "skip/pass",
                      "loop158b": f"{slb.get('skipped')}/{slb.get('pass')}",
                      "loop158c": f"{slg.get('skipped')}/{slg.get('pass')}"})
    if slg.get("reason") != slb.get("reason"):
        note("sleep", "*", "reason", slb.get("reason"), slg.get("reason"))

    skb, skg = load(BASE / "soak-report.json"), load(OUT / "soak-report.json")
    for f in ("completed", "lost", "wrong", "doubled_replies",
              "audit_lost_pairs", "audit_dup_pairs", "audit_wrong_pairs"):
        if skg.get(f) != skb.get(f):
            moves.append({"suite": "soak", "id": "*", "field": f,
                          "loop158b": skb.get(f), "loop158c": skg.get(f)})

    q4b, q4g = load(BASE / "q4-report.json"), load(OUT / "q4-report.json")
    if q4g.get("leaks") != q4b.get("leaks"):
        moves.append({"suite": "q4", "id": "*", "field": "leaks",
                      "loop158b": q4b.get("leaks"),
                      "loop158c": q4g.get("leaks")})
    return {"moves": moves, "allowed": allowed,
            "q4_n": (q4g.get("n_replies"), q4b.get("n_replies"))}


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    run_suites()
    cmp = compare()
    cmp["seconds"] = round(time.time() - t0, 1)
    (ART / "marks158c-compare.json").write_text(
        json.dumps(cmp, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G2 moves={len(cmp['moves'])} allowed(filename)="
          f"{len(cmp['allowed'])} q4_n={cmp['q4_n']} "
          f"in {cmp['seconds']}s", flush=True)
    for m in cmp["moves"]:
        print(f"  MOVE {m}", flush=True)
    for m in cmp["allowed"]:
        print(f"  ALLOWED {m}", flush=True)
    return 1 if cmp["moves"] else 0


if __name__ == "__main__":
    sys.exit(main())
