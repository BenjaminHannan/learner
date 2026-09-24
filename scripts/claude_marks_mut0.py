#!/usr/bin/env python3
"""EXP mut-0: SLEEP mark fails closed (director, 2026-09-24 01:55 UTC).

ONE change, additive only: this file is new. scripts/fable_marks123_all.py
is imported READ-ONLY (never edited, never copied-and-modified).

Problem (director-checked): fable_marks123_all.suite_sleep() returns
"pass": True in BOTH branches while always skipping (make_daemon pins
sleep_threshold=100000, so no suite ever sleeps), and
fable_sleepsmoke206.py is called from no run-all script.

Fail-closed wrapper: whenever the wrapped suite_sleep skips, this runner
reports pass=False, status="NOT-RUN" (rewriting sleep-report.json so),
and any full run-all verdict that includes SLEEP shows NOT-RUN instead
of PASS for the SLEEP row (overall NOT-RUN, never PASS, while SLEEP is
NOT-RUN; FAIL if any non-SLEEP suite fails).

Modes (from the repo root, uv prefix as in the other runners):
  single suite (e.g. --suite sleep):
    python -B scripts/claude_marks_mut0.py --agent <agent> --config <cfg>
      --out <dir> --suite sleep
  full run (delegates legs to the sealed runner, then fail-closes SLEEP):
    python -B scripts/claude_marks_mut0.py --agent <agent> --config <cfg>
      --out <dir> [--suites p2,p3,...]
  run-all verdict combiner (called at the end of the *_runall_mut0.sh):
    python -B scripts/claude_marks_mut0.py --runall-verdict --run-dir <R>
      --regscore <regscore.json> --smoke <smoke-report.json>
      --sleep-out <mut0 sleep out dir> --agent <name> --out <verdict.json>

CPU only. Writes only inside --out / --run-dir (new files).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _load_marks_ro():
    """Import fable_marks123_all read-only (no edit, no copy)."""
    target = SCRIPTS / "fable_marks123_all.py"
    spec = importlib.util.spec_from_file_location(
        "fable_marks123_all_ro", str(target))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


M = _load_marks_ro()
_ORIG_SUITE_SLEEP = M.suite_sleep

NOT_RUN = "NOT-RUN"


def suite_sleep_failclosed(out: Path, agent_script: str,
                           config_path: str) -> dict:
    """Call the sealed suite_sleep, fail closed whenever it skips."""
    rep = dict(_ORIG_SUITE_SLEEP(out, agent_script, config_path))
    if rep.get("skipped"):
        rep["pass"] = False
        rep["status"] = NOT_RUN
        (out / "sleep-report.json").write_text(
            json.dumps(rep, indent=1), encoding="utf-8")
        print(f"SLEEP: {NOT_RUN} (fail-closed mut0) — "
              f"{str(rep.get('reason', ''))[:160]}", flush=True)
    else:
        rep["status"] = "PASS" if rep.get("pass") else "FAIL"
        (out / "sleep-report.json").write_text(
            json.dumps(rep, indent=1), encoding="utf-8")
        print(f"SLEEP: ran -> {rep['status']}", flush=True)
    return rep


def _failclose_out(out: Path) -> dict:
    """Rewrite an already-written full-run out dir so SLEEP fails closed."""
    sp = out / "sleep-report.json"
    rep = json.loads(sp.read_text(encoding="utf-8"))
    if rep.get("skipped"):
        rep["pass"] = False
        rep["status"] = NOT_RUN
        sp.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    sump = out / "fable_marks123_summary.json"
    s = json.loads(sump.read_text(encoding="utf-8"))
    for row in s.get("table", []):
        if row.get("suite") == "sleep" and rep.get("skipped"):
            row["status"] = NOT_RUN
            row["number"] = ("NOT-RUN: " + str(rep.get("reason", "")))[:58]
    others = [r["status"] for r in s.get("table", [])
              if r.get("suite") != "sleep"]
    if rep.get("skipped"):
        s["status"] = (NOT_RUN if all(o in ("PASS", "SKIP") for o in others)
                       else "FAIL")
        s["pass"] = False
    sump.write_text(json.dumps(s, indent=1), encoding="utf-8")
    print(f"mut0 verdict: SLEEP={rep.get('status', NOT_RUN)} "
          f"overall={s.get('status')}", flush=True)
    return s


def run_full_failclosed(agent: str, config: str, out: Path, suites: list,
                        workers: int, soak_turns: int) -> int:
    """Delegate legs to the sealed runner, then fail-close the SLEEP leg.

    The sealed main() re-enters scripts/fable_marks123_all.py per suite
    in subprocesses, so the parent's patch cannot touch the SLEEP child;
    the post-pass (_failclose_out) rewrites that leg's report + summary.
    """
    M.suite_sleep = suite_sleep_failclosed
    try:
        rc = M.main(["--agent", agent, "--config", config,
                     "--out", str(out),
                     "--suites", ",".join(suites),
                     "--workers", str(workers),
                     "--soak-turns", str(soak_turns)])
    finally:
        M.suite_sleep = _ORIG_SUITE_SLEEP
    s = _failclose_out(out)
    return 2 if s.get("status") == NOT_RUN else rc


def smoke_verdict(smoke: dict) -> str:
    """PASS/FAIL per sealed PASSMARKS rule; RAN-ness is checked by caller."""
    try:
        ok = (smoke.get("sleeps_logged", 0) >= 1
              and bool(smoke.get("installed"))
              and smoke.get("sleep_overwrote_taught", 1) == 0
              and smoke.get("taught_good") == smoke.get("taught_total"))
    except (TypeError, AttributeError):
        ok = False
    return "PASS" if ok else "FAIL"


def runall_verdict(run_dir: Path, regscore_path: Path, smoke_path: Path,
                   sleep_out: Path, agent: str, out_path: Path) -> int:
    """Combine one *_runall_mut0.sh run into mut0-verdict.json (fail-closed).

    Overall status is NEVER PASS while SLEEP is NOT-RUN: NOT-RUN when all
    non-SLEEP suites hold, FAIL otherwise.
    """
    t0 = time.time()
    reg = json.loads(regscore_path.read_text(encoding="utf-8"))
    sleep_rep = json.loads((sleep_out / "sleep-report.json").read_text(
        encoding="utf-8"))
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    for key in ("label", "seconds", "sleeps_logged", "installed",
                "probes_right", "probes_wrong", "probes_abstain",
                "taught_good", "taught_total", "taught_dupes",
                "sleep_overwrote_taught", "episodes_at_install"):
        if key not in smoke:
            raise KeyError(f"smoke report missing {key}: "
                           f"not honestly recorded")
    smv = smoke_verdict(smoke)
    non_sleep_ok = (reg.get("verdict") == "PASS")
    sleep_status = sleep_rep.get("status", NOT_RUN)
    status = ("FAIL" if not non_sleep_ok else
              NOT_RUN if sleep_status == NOT_RUN else
              ("PASS" if sleep_rep.get("pass") else "FAIL"))
    verdict = {
        "agent": agent,
        "run_dir": str(run_dir),
        "non_sleep_verdict": reg.get("verdict"),
        "non_sleep_problems": reg.get("problems", []),
        "sleep": {"status": sleep_status, "pass": bool(sleep_rep.get(
            "pass", False)), "skipped": bool(sleep_rep.get(
                "skipped", True)),
            "seconds": sleep_rep.get("seconds")},
        "smoke": {"report": str(smoke_path),
                  "seconds": smoke["seconds"],
                  "sleeps_logged": smoke["sleeps_logged"],
                  "installed": bool(smoke["installed"]),
                  "probes_right": smoke["probes_right"],
                  "probes_wrong": smoke["probes_wrong"],
                  "probes_abstain": smoke["probes_abstain"],
                  "taught": f"{smoke['taught_good']}/{smoke['taught_total']}",
                  "taught_dupes": smoke["taught_dupes"],
                  "sleep_overwrote_taught": smoke["sleep_overwrote_taught"],
                  "verdict": smv},
        "status": status,
        "pass": status == "PASS",
        "seconds": round(time.time() - t0, 1),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    print(f"mut0 run-all verdict: non-SLEEP={verdict['non_sleep_verdict']} "
          f"SLEEP={sleep_status} smoke={smv}({smoke['seconds']}s) "
          f"-> {status}", flush=True)
    return 0 if status == "PASS" else (2 if status == NOT_RUN else 1)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="EXP mut-0 fail-closed SLEEP")
    ap.add_argument("--agent", default="")
    ap.add_argument("--config", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--suite", default="all")
    ap.add_argument("--suites", default="")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--soak-turns", type=int, default=2000)
    ap.add_argument("--runall-verdict", action="store_true")
    ap.add_argument("--run-dir", default="")
    ap.add_argument("--regscore", default="")
    ap.add_argument("--smoke", default="")
    ap.add_argument("--sleep-out", default="")
    args = ap.parse_args(argv)
    if args.runall_verdict:
        return runall_verdict(Path(args.run_dir), Path(args.regscore),
                              Path(args.smoke), Path(args.sleep_out),
                              args.agent, Path(args.out))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.suite != "all":
        if args.suite == "sleep":
            rep = suite_sleep_failclosed(out, args.agent, args.config)
            print(json.dumps({"suite": "sleep",
                              "pass": rep.get("pass"),
                              "status": rep.get("status"),
                              "seconds": rep.get("seconds")}))
            return 0 if rep.get("pass") else 2
        rep = M.run_single_suite(args.suite, str(out), args.agent,
                                 args.config, args.soak_turns)
        print(json.dumps({"suite": args.suite, "pass": rep.get("pass"),
                          "seconds": rep.get("seconds")}))
        return 0 if rep.get("pass") else 1
    suites = [s for s in (args.suites.split(",") if args.suites else M.SUITES)
              if s in M.SUITES]
    return run_full_failclosed(args.agent, args.config, out, suites,
                               args.workers, args.soak_turns)


if __name__ == "__main__":
    sys.exit(main())
