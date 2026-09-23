#!/usr/bin/env python3
"""Experiment 154e -- L1 probe driver (registered runs only).

Same contract as scripts/fable_fix154c_probe.py, agent swapped to
Loop154eAgentLoop. Reads sealed case file, compares replies EXACTLY,
checks state maps. Outputs probe154e_results.jsonl + probe154e_summary.json.
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
import fable_loop154e_agent as L154e  # noqa: E402 (agent under test)


def notebook_state(loop) -> dict[str, list[str]]:
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
    ap = argparse.ArgumentParser(description="Exp 154e L1 probe")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state-dir", required=False, default=None)
    args = ap.parse_args(argv)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    cases = [json.loads(line) for line in
             Path(args.cases).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    base = args.state_dir or tempfile.mkdtemp(prefix="probe154e_")
    seg = 0
    loop = L154e.build_agent154e(
        {"state_dir": str(Path(base) / f"seg{seg}")})
    t0 = time.time()
    results: list[dict] = []
    npass = 0
    for case in cases:
        if case.get("reset"):
            seg += 1
            loop = L154e.build_agent154e(
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
    (outdir / "probe154e_results.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in results) + "\n", encoding="utf-8")
    (outdir / "probe154e_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
