#!/usr/bin/env python3
"""Experiment 154f -- N1 probe driver (registered runs only).

Reads sealed case154f.jsonl, compares replies EXACTLY, checks state
maps and write flags (writes "0" = 0 new events, "w" = >=1 new event).
Outputs probe154f_results.jsonl + probe154f_summary.json.
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
import fable_loop154f_agent as L154f  # noqa: E402 (agent under test)


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
        key = f"{nb.entities[subject]}|{relation}"
        vals = [M154.display154b(nb, r["value"]) for r in rows]
        if vals:
            pairs[key] = vals
        elif key.split("|")[0] in ("Kim", "Ana", "Raj", "Eli", "Max", "Zoe"):
            pairs[key] = []
    return pairs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 154f N1 probe")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state-dir", required=False, default=None)
    args = ap.parse_args(argv)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    cases = [json.loads(line) for line in
             Path(args.cases).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    base = args.state_dir or tempfile.mkdtemp(prefix="probe154f_")
    seg = 0
    loop = L154f.build_agent154f(
        {"state_dir": str(Path(base) / f"seg{seg}")})
    t0 = time.time()
    results: list[dict] = []
    npass = 0
    for case in cases:
        if case.get("reset"):
            seg += 1
            loop = L154f.build_agent154f(
                {"state_dir": str(Path(base) / f"seg{seg}")})
            results.append({"reset": True, "pass": True})
            npass += 1
            continue
        eb = len(loop.nb.events)
        said = " ".join(loop.turn(case["turn"])) if case.get("turn") else ""
        nev = len(loop.nb.events) - eb
        reply_ok = (said == case.get("expect", said)) if case.get("turn") \
            else True
        writes_ok = True
        if case.get("writes") == "0" and nev != 0:
            writes_ok = False
        if case.get("writes") == "w" and nev < 1:
            writes_ok = False
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
        ok = bool(reply_ok and writes_ok and state_ok and
                  (full_ok is not False))
        npass += int(ok)
        results.append({"n": case["n"], "turn": case.get("turn"),
                        "reply": said, "expect": case.get("expect"),
                        "pass": ok, "reply_ok": bool(reply_ok),
                        "writes_ok": bool(writes_ok), "nev": nev,
                        "state_ok": bool(state_ok),
                        "full_state_ok": full_ok,
                        "state_got": state_got or None})
        if not ok:
            print(f"MISS n={case['n']} turn={case.get('turn')!r}\n"
                  f"  got    {said!r}\n  wanted {case.get('expect')!r}\n"
                  f"  writes_ok={writes_ok} (nev={nev}) state_ok={state_ok} "
                  f"full_ok={full_ok}", flush=True)
    n_scored = sum(1 for r in results if "turn" in r or "reset" in r)
    summary = {"n": n_scored, "pass": npass,
               "verdict": "PASS" if npass == n_scored else "FAIL",
               "seconds": round(time.time() - t0, 1)}
    (outdir / "probe154f_results.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in results) + "\n", encoding="utf-8")
    (outdir / "probe154f_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
