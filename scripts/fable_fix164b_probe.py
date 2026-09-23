#!/usr/bin/env python3
"""Experiment 164b -- A1/A2 sealed probe runner (fresh registration).

Reads FROZEN dialogues from artifacts/fable-about164b-20260922/cases164b.json
(50 dialogues: 25 about-X incl. USER facts, 8 unknown-X, 5 bare summary, 12
near-misses), each through FRESH in-process loops. Triples via
fable_loop90_agent.notebook_triples. Every seed/case reported, never averaged.

Judgements:
  A/B/C (must-cases): about/summary-turn reply EXACTLY equals the frozen
    literal, FACT-event delta on every about/summary turn is 0 (A1: 0 writes
    on every about-turn), final triples equal the frozen literal.
    Verdict OK/FAIL.
  D (near-miss): every reply byte-equal loop164b vs loop138h AND total FACT
    writes equal (A2 events check on near-miss turns). Verdict OK/FAIL.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix164b_probe.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop138h_agent as L138H  # noqa: E402 (base arm, read-only)
import fable_loop164b_agent as L164B  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART164B = ROOT / "artifacts" / "fable-about164b-20260922"


def fresh(build_fn):
    tmp = tempfile.mkdtemp(prefix="p164b_")
    return build_fn({"state_dir": tmp, "sleep_threshold": 100000})


def fact_events(loop) -> int:
    return sum(1 for e in loop.nb.events if e.get("kind") == "FACT")


def run_dialogue(loop, turns: list[str]) -> dict:
    replies, deltas = [], []
    for t in turns:
        f0 = fact_events(loop)
        replies.append(" ".join(loop.turn(t)))
        deltas.append(fact_events(loop) - f0)
    return {"replies": replies, "fact_deltas": deltas,
            "fact_writes": sum(deltas),
            "triples": sorted([list(t) for t in L90.notebook_triples(
                loop.nb)])}


def check_must(row: dict) -> dict:
    got = run_dialogue(fresh(L164B.build_agent164b), row["turns"])
    checks = [(row["ask_idx"], row["expect_reply"])]
    if "expect_reply2" in row:
        checks.append((2, row["expect_reply2"]))
    ok_replies = all(got["replies"][i] == e for i, e in checks)
    ok_writes = all(got["fact_deltas"][i] == 0 for i, _ in checks)
    ok_triples = got["triples"] == sorted(row["expect_triples"])
    ok = ok_replies and ok_writes and ok_triples
    return {"id": row["id"], "group": row.get("group", "?"),
            "turns": row["turns"], "replies": got["replies"],
            "fact_deltas": got["fact_deltas"], "triples": got["triples"],
            "expect": row["expect_reply"], "expect_triples": row[
                "expect_triples"],
            "ok_replies": ok_replies, "ok_writes": ok_writes,
            "ok_triples": ok_triples,
            "verdict": "OK" if ok else "FAIL"}


def check_near(row: dict) -> dict:
    got = run_dialogue(fresh(L164B.build_agent164b), row["turns"])
    base = run_dialogue(fresh(L138H.build_agent138h), row["turns"])
    ok = (got["replies"] == base["replies"]
          and got["fact_writes"] == base["fact_writes"])
    return {"id": row["id"], "group": "D", "turns": row["turns"],
            "replies164b": got["replies"], "replies138h": base["replies"],
            "writes164b": got["fact_writes"],
            "writes138h": base["fact_writes"],
            "verdict": "OK" if ok else "FAIL"}


def main() -> int:
    t0 = time.time()
    cases = json.loads((ART164B / "cases164b.json").read_text(
        encoding="utf-8"))
    rows: list[dict] = []
    for grp, fn in (("A", check_must), ("B", check_must), ("C", check_must)):
        for row in cases[grp]:
            rows.append(fn({**row, "group": grp}))
    for row in cases["D"]:
        rows.append(check_near(row))
    counts: dict = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    groups: dict = {}
    for r in rows:
        g = groups.setdefault(r["group"], {})
        g[r["verdict"]] = g.get(r["verdict"], 0) + 1
    out = {"seconds": round(time.time() - t0, 1), "counts": counts,
           "by_group": groups, "rows": rows}
    (ART164B / "probe164b-loop164b.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"probe164b: {counts} by_group={groups} "
          f"seconds={out['seconds']}", flush=True)
    for r in rows:
        if r["verdict"] != "OK":
            print(f"  FAIL {r['id']}: {json.dumps(r)[:500]}", flush=True)
    return 0 if counts.get("FAIL", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
