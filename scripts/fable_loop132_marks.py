#!/usr/bin/env python3
"""Experiment 132 marks (Q4): P2/P3/P4 + red-team-124, base loop121 vs loop132.

Copy of the exp-121 marks shape with ONLY the agent classes changed (agent
class swaps, as prior briefs allow):

  P2  all 64 sealed red-team-98 cases through Loop132Daemon, judged with the
      unchanged redteam98 judge; every verdict move vs the sealed run-2 AND
      vs the base loop121 arm listed.
  P3  loop96 marks L1-L6 re-run with the loop132 agent swapped in (runtime
      monkeypatch of the imported module objects only; no file edited).
  P4  30 sealed innocent sentences through Loop132Daemon; false refusals gate
      (must equal the sealed loop102 outcome: 0 false refusals, 0 nonpass).
  RT124  red-team-124's sealed cases through loop121-before and loop132-after
      (fresh daemon dir per case per arm, mailbox files), verdicts ONLY from
      the runner's check_case with the loop113b expectations (arm label
      "loop113b", exactly as the director/exp-113d did); reports the full
      before/after list, prefix-answer count, and new wrong writes.

Sealed artifacts and other modules are read, never written. Reports land
under artifacts/fable-bench132-20260922/ (never in another folder).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed, as part of the
registered exp-132 wave):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop132_marks.py --mark all
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop121_agent as L121  # noqa: E402 (before arm, read-only)
import fable_loop132_agent as L132  # noqa: E402 (after arm, read-only)
import fable_marks123_all as M123  # noqa: E402 (P2/P3/P4 suites, read-only)
import fable_redteam124_runner as R124  # noqa: E402 (judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench132-20260922" / "regression"
CASES_PATH = ROOT / "artifacts" / "fable-redteam124-20260922" \
    / "fable_redteam124_cases.json"

AGENT132 = str(SCRIPTS / "fable_loop132_agent.py")
AGENT121 = str(SCRIPTS / "fable_loop121_agent.py")


def ensure_configs() -> tuple[str, str]:
    cfgdir = ART.parent
    cfgdir.mkdir(parents=True, exist_ok=True)
    c121 = cfgdir / "loop121-config.json"
    c132 = cfgdir / "loop132-config.json"
    if not c121.exists():
        c121.write_text(json.dumps(copy.deepcopy(L121.DEFAULT_CONFIG121),
                                   indent=1), encoding="utf-8")
    if not c132.exists():
        c132.write_text(json.dumps(copy.deepcopy(L132.DEFAULT_CONFIG132),
                                   indent=1), encoding="utf-8")
    return str(c121), str(c132)


def run_p2(out: Path, cfg132: str) -> dict:
    return M123.suite_p2(out, AGENT132, cfg132)


def run_p3(out: Path, cfg132: str) -> dict:
    return M123.suite_p3(out, AGENT132, cfg132)


def run_p4(out: Path, cfg132: str) -> dict:
    return M123.suite_p4(out, AGENT132, cfg132)


def make_daemon124(arm: str, workdir: Path):
    if arm == "loop121":
        cfg = copy.deepcopy(L121.DEFAULT_CONFIG121)
        cfg["state_dir"] = str(workdir)
        cfg["sleep_threshold"] = 10 ** 9
        return L121.Loop121Daemon(str(workdir), cfg=cfg, idle_seconds=30.0)
    cfg = copy.deepcopy(L132.DEFAULT_CONFIG132)
    cfg["state_dir"] = str(workdir)
    cfg["sleep_threshold"] = 10 ** 9
    return L132.Loop132Daemon(str(workdir), cfg=cfg, idle_seconds=30.0)


def run_case_ours(case: dict, arm: str, workdir: Path) -> dict:
    """Same shape as the 113d runner with the daemon class swapped."""
    rec = {"id": case["id"], "family": case["family"], "arm": "loop113b",
           "turns": [], "verdict": "OK", "reasons": []}
    try:
        daemon = make_daemon124(arm, workdir)
    except Exception as exc:  # noqa: BLE001
        rec["verdict"] = "HARNESS-ERROR"
        rec["reasons"].append(f"boot failed: {exc!r}")
        return rec
    nb = daemon.loop.nb
    allowed = set(tuple(f) for f in case.get("allowed_facts", []))
    for i, step in enumerate(case["steps"]):
        text = step["text"]
        before = set(tuple(t) for t in L90.notebook_triples(nb))
        fname = f"t{i:02d}.txt"
        try:
            (workdir / "inbox" / fname).write_text(text, encoding="utf-8")
            daemon.process_file(workdir / "inbox" / fname)
            reply = (workdir / "outbox" / fname).read_text(
                encoding="utf-8").strip()
            stage = str(getattr(daemon.loop.ears, "last_stage", ""))
        except Exception as exc:  # noqa: BLE001
            rec["turns"].append({"i": i, "text": text, "reply": "",
                                 "error": repr(exc)})
            rec["verdict"] = "HARNESS-ERROR"
            rec["reasons"].append(f"turn {i} raised {exc!r}")
            return rec
        after = set(tuple(t) for t in L90.notebook_triples(nb))
        added = sorted(list(after - before))
        wrong = [t for t in added if tuple(t) not in allowed]
        rec["turns"].append({"i": i, "text": text, "reply": reply,
                             "added": added, "wrong_writes": wrong,
                             "stage": stage})
    return rec


def run_rt124(out: Path) -> dict:
    t0 = time.time()
    suite = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    cases = suite["cases"]
    workroot = out / "rt124-tmp"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    recs: dict[str, list] = {}
    for arm in ("loop121", "loop132"):
        recs[arm] = []
        for case in cases:
            workdir = workroot / arm / case["id"]
            workdir.mkdir(parents=True, exist_ok=True)
            rec = run_case_ours(case, arm, workdir)
            if rec["verdict"] != "HARNESS-ERROR":
                R124.check_case(case, rec, markers)
            recs[arm].append(rec)
            print(f"{arm} {case['id']}: {rec['verdict']}", flush=True)
    rows = []
    for bc, ac in zip(recs["loop121"], recs["loop132"]):
        assert bc["id"] == ac["id"]
        brows = [r for r in bc["reasons"]]
        arows = [r for r in ac["reasons"]]
        b_wrong = sorted({r for r in brows if "wrong writes" in r})
        a_wrong = sorted({r for r in arows if "wrong writes" in r})
        new_wrong = sorted(set(a_wrong) - set(b_wrong))
        rows.append({
            "id": bc["id"], "family": bc["family"],
            "before": bc["verdict"], "after": ac["verdict"],
            "before_reasons": brows, "after_reasons": arows,
            "before_final": bc["turns"][-1]["reply"][:200] if bc["turns"]
            else "",
            "after_final": ac["turns"][-1]["reply"][:200] if ac["turns"]
            else "",
            "before_wrong_writes": b_wrong, "after_wrong_writes": a_wrong,
            "new_wrong_writes": new_wrong,
            "before_stage": bc["turns"][-1].get("stage", "") if bc["turns"]
            else "",
            "after_stage": ac["turns"][-1].get("stage", "") if ac["turns"]
            else "",
        })
    n = len(rows)
    ok_to_bug = [r["id"] for r in rows
                 if r["before"] == "OK" and r["after"] != "OK"]
    bug_to_ok = [r["id"] for r in rows
                 if r["before"] != "OK" and r["after"] == "OK"]
    still_bug = [r["id"] for r in rows if r["after"] != "OK"]
    all_new_wrong = {r["id"]: r["new_wrong_writes"] for r in rows
                     if r["new_wrong_writes"]}
    prefix_after = [r["id"] for r in rows
                    if r["after"] != "OK" and any(
                        "abstain missed" in x for x in r["after_reasons"])]
    rep = {
        "mark": "RT124", "seconds": round(time.time() - t0, 1), "n": n,
        "rows": rows,
        "ok_before_stay_ok": [r["id"] for r in rows
                              if r["before"] == "OK" and r["after"] == "OK"],
        "ok_to_bug": ok_to_bug, "bug_to_ok": bug_to_ok,
        "still_bug": still_bug, "prefix_after": prefix_after,
        "new_wrong_writes": all_new_wrong,
        "pass": len(prefix_after) == 0 and len(all_new_wrong) == 0
        and len(ok_to_bug) == 0,
    }
    (out / "rt124-report.json").write_text(json.dumps(rep, indent=1),
                                           encoding="utf-8")
    print(f"RT124: n={n} ok_to_bug={ok_to_bug} bug_to_ok={bug_to_ok} "
          f"still_bug={still_bug}")
    print(f"RT124: prefix_after={prefix_after} new_wrong={all_new_wrong} "
          f"-> {'PASS' if rep['pass'] else 'FAIL'} ({rep['seconds']} s)")
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 132 Q4 marks")
    ap.add_argument("--mark", default="all",
                    choices=["all", "p2", "p3", "p4", "rt124"])
    args = ap.parse_args(argv)
    ART.mkdir(parents=True, exist_ok=True)
    _c121, c132 = ensure_configs()
    out = ART
    reps: dict[str, dict] = {}
    if args.mark in ("all", "p2"):
        reps["p2"] = run_p2(out, c132)
    if args.mark in ("all", "p3"):
        reps["p3"] = run_p3(out, c132)
    if args.mark in ("all", "p4"):
        reps["p4"] = run_p4(out, c132)
    if args.mark in ("all", "rt124"):
        reps["rt124"] = run_rt124(out)
    (out / "fable_loop132_marks_summary.json").write_text(
        json.dumps({k: {"pass": v.get("pass"),
                        "seconds": v.get("seconds")} for k, v in reps.items()},
                   indent=1), encoding="utf-8")
    ok = all(v.get("pass") for v in reps.values())
    print(f"MARKS132 {sorted(reps)} -> {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
