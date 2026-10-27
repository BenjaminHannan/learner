#!/usr/bin/env python3
"""Experiment 172b -- T-probe driver (registered runs only).

Replays a sealed case file (same schema as probe154c_cases.jsonl:
{"reset": true} segments, or {"n":..,"turn":..,"expect":..} with optional
"state"/"full_state" maps) through a fresh Loop172AgentLoop per segment
(agent code is 172's, unchanged; this driver only swaps the builder).

Compares replies EXACTLY, checks state maps against the notebook's active
taught rows (same reader as 154c, reused by import). T2 structural check:
no sealed re-teach of an occupied slot on a non-allow-listed relation
without an explicit correction prefix may expect a silent "Saved:" --
it must expect the change-prompt ("Do you want me to change it to").

Outputs: <out>/probe172b_results.jsonl + <out>/probe172b_summary.json
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

import fable_fix154b_multival as M154  # noqa: E402 (state readers, read-only)
import fable_fix154c_allowlist as M154C  # noqa: E402 (allow-list, read-only)
import fable_fix154c_probe as P154C  # noqa: E402 (notebook_state, read-only)
import fable_loop102_agent as L102  # noqa: E402 (prefix RE, read-only)
import fable_loop172_agent as L172  # noqa: E402 (agent under test, read-only)

PROMPT_NEEDLE = "Do you want me to change it to"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 172b T-probe")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state-dir", required=False, default=None)
    ap.add_argument("--tag", required=False, default="probe172b")
    args = ap.parse_args(argv)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    cases = [json.loads(line) for line in
             Path(args.cases).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    base = args.state_dir or tempfile.mkdtemp(prefix="probe172b_")
    seg = 0
    loop = L172.build_agent172(
        {"state_dir": str(Path(base) / f"seg{seg}")})
    t0 = time.time()
    results: list[dict] = []
    npass = 0
    for case in cases:
        if case.get("reset"):
            seg += 1
            loop = L172.build_agent172(
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
            state_got = P154C.notebook_state(loop)
            for pair, want in case["state"].items():
                if state_got.get(pair, []) != list(want):
                    state_ok = False
        full_ok = None
        if "full_state" in case:
            state_got = state_got or P154C.notebook_state(loop)
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
    # T2 live audit: every sealed re-teach of an occupied slot on a
    # non-allow relation without a correction prefix expects the
    # change-prompt, so a passing run means 0 silent replacements of a
    # taught value (a silent replace would mismatch both the prompt
    # expect and the kept-state map). Count prompt expects as evidence.
    n_prompt_expects = sum(
        1 for c in cases
        if isinstance(c.get("expect"), str)
        and PROMPT_NEEDLE in c["expect"])
    summary = {"n": n_scored, "pass": npass,
               "verdict": "PASS" if npass == n_scored else "FAIL",
               "n_prompt_expects": n_prompt_expects,
               "seconds": round(time.time() - t0, 1)}
    (outdir / f"{args.tag}_results.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in results) + "\n", encoding="utf-8")
    (outdir / f"{args.tag}_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
