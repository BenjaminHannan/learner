#!/usr/bin/env python3
"""Experiment 154c -- T1/T1b probe driver (registered runs only).

Reads a cases JSONL (sealed): each line either
  {"reset": true}  (start a fresh Loop154cAgentLoop; segments isolate the
   yes/no pending state) or
  {"n": 1, "turn": "...", "expect": "Saved: ..."}
  optional "state": {"Omar|sister": ["Priya", "Lena"]} checked after the turn,
  optional "full_state" on the last line of a segment.

Runs all turns IN ORDER (fresh loop per segment), compares replies
EXACTLY, checks state maps against the notebook's active taught rows:
  probe154c_results.jsonl + probe154c_summary.json

T2 (0 wrong writes, 0 lost values) = every expect passes AND every state
map passes AND the final full_state map matches exactly.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix154b_multival as M154  # noqa: E402 (state readers)
import fable_loop154c_agent as L154c  # noqa: E402 (agent under test)


def notebook_state(loop) -> dict[str, list[str]]:
    """Every (subject, relation) -> current taught displays (oldest first)."""
    nb = loop.nb
    pairs: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    for fact in nb.facts.values():
        if fact.get("source") != "taught":
            continue
        seen.add((fact["subject"], fact["relation"]))
    for subject, relation in sorted(seen):
        rows = M154.taught_current154b(nb, subject, relation)
        if rows:
            key = f"{nb.entities[subject]}|{relation}"
            pairs[key] = [M154.display154b(nb, r["value"]) for r in rows]
    return pairs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 154c T-probe")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state-dir", required=False, default=None)
    args = ap.parse_args(argv)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    cases = [json.loads(line) for line in
             Path(args.cases).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    base = args.state_dir or tempfile.mkdtemp(prefix="probe154c_")
    seg = 0
    loop = L154c.build_agent154c(
        {"state_dir": str(Path(base) / f"seg{seg}")})
    t0 = time.time()
    results: list[dict] = []
    npass = 0
    for case in cases:
        if case.get("reset"):
            seg += 1
            loop = L154c.build_agent154c(
                {"state_dir": str(Path(base) / f"seg{seg}")})
            results.append({"reset": True, "pass": True})
            npass += 1
            continue
        before_facts = set(loop.nb.facts)
        said = " ".join(loop.turn(case["turn"])) if case.get("turn") else ""
        new_facts = sorted(set(loop.nb.facts) - before_facts)
        reply_ok = (said == case.get("expect", said)) if case.get("turn") \
            else True
        state_ok, state_got = True, {}
        if "state" in case:
            state_got = notebook_state(loop)
            for pair, want in case["state"].items():
                if state_got.get(pair, []) != list(want):
                    state_ok = False
        full_ok = None
        if "full_state" in case:
            state_got = state_got or notebook_state(loop)
            full_ok = (state_got == case["full_state"])
        ok = bool(reply_ok and state_ok and (full_ok is not False))
        npass += int(ok)
        results.append({"n": case["n"], "turn": case.get("turn"),
                        "reply": said, "expect": case.get("expect"),
                        "pass": ok, "reply_ok": bool(reply_ok),
                        "state_ok": bool(state_ok),
                        "full_state_ok": full_ok,
                        "new_facts": new_facts,
                        "state_got": state_got or None})
        if not ok:
            print(f"MISS n={case['n']} turn={case.get('turn')!r}\n"
                  f"  got    {said!r}\n  wanted {case.get('expect')!r}\n"
                  f"  state_ok={state_ok} full_ok={full_ok}", flush=True)
    n_scored = sum(1 for r in results if "turn" in r or "reset" in r)
    summary = {"n": n_scored, "pass": npass,
               "verdict": "PASS" if npass == n_scored else "FAIL",
               "seconds": round(time.time() - t0, 1)}
    (outdir / "probe154c_results.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in results) + "\n", encoding="utf-8")
    (outdir / "probe154c_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
