#!/usr/bin/env python3
"""Experiment 209 -- W1/W2 probe driver (Muse).

W1: cases209-badsave.json on loop209 -- every stored taught fact exactly
    as expected (subject display, relation, literal-vs-entity + text),
    reply contains/exactly the expected text; 0 bad saves.
W2: cases209-nearmiss.json on loop138i AND loop209, fresh loop per case
    per agent -- replies, stored taught facts (with value kinds), entity
    names, and FACT-event counts byte-identical.

Pilot use: --out <scratch dir> (outside artifacts/).
Registered use (only AFTER PASSMARKS.md is sealed): --out
artifacts/fable-writescreen209-20260922/probe (small JSON only).

Run (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_writescreen209_probe.py --out <dir>
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138i_agent as L138I  # noqa: E402 (base, read-only)
import fable_loop209_agent as L209  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART209 = ROOT / "artifacts" / "fable-writescreen209-20260922"


def fresh209():
    d = tempfile.mkdtemp(prefix="w209-")
    cfg = copy.deepcopy(L209.DEFAULT_CONFIG209)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    return L209.build_agent209(cfg)


def fresh138i():
    d = tempfile.mkdtemp(prefix="w138i-")
    cfg = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    return L138I.build_agent138i(cfg)


def snapshot(loop) -> dict:
    nb = loop.nb
    stored = []
    for fact in nb.facts.values():
        if fact.get("source") != "taught" or not nb.active(fact["fact_id"]):
            continue
        val = fact["value"]
        if "literal" in val:
            stored.append([nb.entities.get(fact["subject"], "?"),
                           fact["relation"], "literal", str(val["literal"])])
        else:
            stored.append([nb.entities.get(fact["subject"], "?"),
                           fact["relation"], "entity",
                           nb.entities.get(val["entity"], "?")])
    stored.sort()
    rels = sorted(e["relation"] for e in nb.events if e["kind"] == "RELATION")
    facts_n = sum(1 for e in nb.events if e["kind"] == "FACT")
    return {"stored": stored, "entities": sorted(nb.entities.values()),
            "relations": rels, "fact_events": facts_n}


def run_turns(loop, turns: list[str]) -> list[str]:
    return [(" ".join(loop.turn(t))).strip() for t in turns]


def load_cases(name: str) -> list[dict]:
    return json.loads((ART209 / name).read_text(encoding="utf-8"))["cases"]


def w1(out: Path) -> dict:
    t0 = time.time()
    rows = []
    for case in load_cases("cases209-badsave.json"):
        loop = fresh209()
        replies = run_turns(loop, case["turns"])
        snap = snapshot(loop)
        ok_stored = snap["stored"] == sorted(case["expect_stored"])
        if "expect_reply_exact" in case:
            ok_reply = replies[-1] == case["expect_reply_exact"]
        else:
            ok_reply = case["expect_reply"] in replies[-1]
        ok_norel = True
        if not case["expect_stored"]:
            ok_norel = snap["relations"] == []
        ok = ok_stored and ok_reply and ok_norel
        # informational: does the base show the bad save?
        base = fresh138i()
        base_replies = run_turns(base, case["turns"])
        base_snap = snapshot(base)
        rows.append({"id": case["id"], "group": case["group"],
                     "pass": ok, "stored": snap["stored"],
                     "reply": replies[-1][:200],
                     "base_stored": base_snap["stored"],
                     "base_reply": base_replies[-1][:200],
                     "base_differs": (base_snap["stored"] != snap["stored"]
                                      or base_replies[-1] != replies[-1])})
        print(f"W1 {case['id']}: {'PASS' if ok else 'FAIL'} "
              f"stored={snap['stored']} reply={replies[-1][:90]!r}",
              flush=True)
    bad = [r["id"] for r in rows if not r["pass"]]
    rep = {"mark": "W1", "n": len(rows), "bad": bad,
           "pass": len(bad) == 0, "seconds": round(time.time() - t0, 1),
           "rows": rows}
    (out / "w1-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    return rep


def w2(out: Path) -> dict:
    t0 = time.time()
    rows = []
    for case in load_cases("cases209-nearmiss.json"):
        base = fresh138i()
        base_replies = run_turns(base, case["turns"])
        base_snap = snapshot(base)
        new = fresh209()
        new_replies = run_turns(new, case["turns"])
        new_snap = snapshot(new)
        same = (base_replies == new_replies and base_snap == new_snap)
        rows.append({"id": case["id"], "group": case["group"],
                     "pass": same, "replies": new_replies,
                     "stored": new_snap["stored"],
                     "base_replies": None if same else base_replies,
                     "base_stored": None if same else base_snap["stored"]})
        print(f"W2 {case['id']}: {'PASS' if same else 'FAIL'} "
              f"reply={new_replies[-1][:90]!r}", flush=True)
    bad = [r["id"] for r in rows if not r["pass"]]
    rep = {"mark": "W2", "n": len(rows), "bad": bad,
           "pass": len(bad) == 0, "seconds": round(time.time() - t0, 1),
           "rows": rows}
    (out / "w2-report.json").write_text(json.dumps(rep, indent=1),
                                        encoding="utf-8")
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 209 W1/W2 probe")
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="all", choices=["all", "w1", "w2"])
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    reps = {}
    if args.only in ("all", "w1"):
        reps["w1"] = w1(out)
    if args.only in ("all", "w2"):
        reps["w2"] = w2(out)
    ok = all(r["pass"] for r in reps.values())
    print(json.dumps({k: {"pass": v["pass"], "n": v["n"],
                          "bad": v["bad"],
                          "seconds": v["seconds"]}
                      for k, v in reps.items()}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
