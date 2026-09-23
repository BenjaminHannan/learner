#!/usr/bin/env python3
"""Exp 129a Q2 -- all 62 sealed exp-110 cases re-run on loop129a.

SEALED exp-110 harness unchanged (run_case mailbox semantics + judge from
scripts/fable_redteam110_runner.py, sealed cases + sealed results for
comparison); only the daemon under test is loop129a (daemon_cmd swap, real
subprocess daemons). Compares per-case verdicts against the sealed exp-110
verdicts AND against the reported loop117 q2-report (F3 identity check:
0 OK->BUG, BUG->OK exactly F5+M5, still-BUG exactly R4/N6/S3/S6).

Writes: artifacts/fable-fix129-20260922/q2-129a-report.json
Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop129a_q2.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix129_common as C129  # noqa: E402 (this experiment)
import fable_redteam110_runner as R110  # noqa: E402 (sealed harness)

ROOT = SCRIPTS.parent
ART110 = ROOT / "artifacts" / "fable-redteam110-20260921"
ART117 = ROOT / "artifacts" / "fable-loop117-20260922"
ART = C129.ART129
CONFIG129A = ART / "loop129a-config.json"

_EXPECT_STAY_BUG = {"R4", "N6", "S3", "S6"}


def daemon_cmd129a(root: Path) -> list[str]:
    return ["uv", "run", "--offline", "--no-project", "--python", "3.12",
            "--with", "torch", "--with", "numpy", "python", "-B",
            str(SCRIPTS / "fable_loop129a_agent.py"),
            "--daemon", "--dir", str(root), "--config", str(CONFIG129A),
            "--idle-seconds", "3600"]


def main() -> int:
    R110.daemon_cmd = daemon_cmd129a  # runtime swap only; no file edited
    ART.mkdir(parents=True, exist_ok=True)
    workroot = ART / "q2-129a-tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ART110 / "fable_redteam110_cases.json").read_text(
        encoding="utf-8"))
    sealed = json.loads((ART110 / "fable_redteam110_results.json").read_text(
        encoding="utf-8"))
    sealed_verdict = {c["id"]: c.get("verdict") for c in sealed["cases"]}
    rep117 = json.loads((ART117 / "q2-report.json").read_text(
        encoding="utf-8"))
    v117 = {r["id"]: r["loop117_verdict"] for r in rep117["rows"]}
    t0 = time.time()
    rows = []
    for case in cases:
        res = R110.run_case(case, workroot)
        verdict = R110.judge(case, res)
        res.update(verdict)
        rows.append({
            "id": case["id"], "group": case["group"],
            "sealed_verdict": sealed_verdict[case["id"]],
            "loop117_verdict": v117.get(case["id"]),
            "loop129a_verdict": verdict["verdict"],
            "reason": verdict.get("reason", "")[:200],
            "log": [{"file": e.get("file"), "reply": e.get("reply"),
                      "statuses": e.get("statuses"),
                      "fact_writes": e.get("fact_writes")}
                     for e in res.get("log", [])]})
        print(f"Q2-129a {case['id']:>3} sealed={sealed_verdict[case['id']]:13} "
              f"117={str(v117.get(case['id'])):13} "
              f"129a={verdict['verdict']:13} "
              f"{verdict.get('reason', '')[:80]}", flush=True)
    ok_to_bug = [r["id"] for r in rows
                 if r["sealed_verdict"] == "OK"
                 and r["loop129a_verdict"] != "OK"]
    bug_to_ok = [r["id"] for r in rows
                 if r["sealed_verdict"] == "BUG"
                 and r["loop129a_verdict"] == "OK"]
    still_bug = [r["id"] for r in rows
                 if r["loop129a_verdict"] == "BUG"]
    herr = [r["id"] for r in rows
            if r["loop129a_verdict"] == "HARNESS-ERROR"]
    diff117 = [r["id"] for r in rows
               if r["loop117_verdict"] != r["loop129a_verdict"]]
    unexpected_stay = [i for i in still_bug if i not in _EXPECT_STAY_BUG]
    passed = (len(ok_to_bug) == 0 and len(herr) == 0
              and set(bug_to_ok) >= {"F5", "M5"}
              and len(unexpected_stay) == 0)
    rep = {"mark": "Q2-129a", "n": len(rows), "ok_to_bug": ok_to_bug,
           "bug_to_ok": bug_to_ok, "still_bug": still_bug,
           "harness_errors": herr, "expected_stay_bug": sorted(
               _EXPECT_STAY_BUG),
           "diff_vs_loop117": diff117,
           "pass": bool(passed), "seconds": round(time.time() - t0, 1),
           "rows": rows}
    (ART / "q2-129a-report.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"Q2-129a: OK->BUG={ok_to_bug} BUG->OK={bug_to_ok} "
          f"stillBUG={still_bug} HARNESS-ERROR={herr} "
          f"diff-vs-117={diff117} -> {'PASS' if passed else 'FAIL'} "
          f"({rep['seconds']} s)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
