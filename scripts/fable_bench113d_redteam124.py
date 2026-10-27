#!/usr/bin/env python3
"""Experiment 113d D1: red-team-124's 62 sealed cases through loop113d.

Director protocol, repeated exactly: each sealed case runs in a FRESH
daemon dir through the mailbox (inbox file -> process_file -> outbox
reply), once on loop113c (before) and once on loop113d (after); verdicts
come ONLY from the runner's check_case with the loop113b expectations
(arm label "loop113b", exactly as the director did -- no ask_abstain_102
extras). Reports the full before/after list, the prefix-answer count
(cases whose final reply answers fewer relations than asked), and new
wrong writes.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench113d_redteam124.py --run
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

import fable_loop113c_agent as L113C  # noqa: E402 (before arm, read-only)
import fable_loop113d_agent as L113D  # noqa: E402 (after arm, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_redteam124_runner as R124  # noqa: E402 (judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench113d-20260922"
CASES_PATH = ROOT / "artifacts" / "fable-redteam124-20260922" \
    / "fable_redteam124_cases.json"

CFG113C = copy.deepcopy(L113C.DEFAULT_CONFIG113C)
CFG113D = copy.deepcopy(L113D.DEFAULT_CONFIG113D)


def make_daemon(arm: str, workdir: Path):
    cfg = copy.deepcopy(CFG113C if arm == "loop113c" else CFG113D)
    cfg["state_dir"] = str(workdir)
    cfg["sleep_threshold"] = 10 ** 9
    if arm == "loop113c":
        return L113C.Loop113cDaemon(str(workdir), cfg=cfg, idle_seconds=30.0)
    return L113D.Loop113dDaemon(str(workdir), cfg=cfg, idle_seconds=30.0)


def cmd_run(_args) -> int:
    suite = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    cases = suite["cases"]
    workroot = ART / "scratch124"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    out: dict = {"seconds": 0.0, "arms": {}, "rows": []}
    recs: dict = {}
    for arm in ("loop113c", "loop113d"):
        recs[arm] = []
        for case in cases:
            workdir = workroot / arm / case["id"]
            workdir.mkdir(parents=True, exist_ok=True)
            # Our factories; verdicts ONLY from the runner's check_case
            # with the loop113b expectations (arm label "loop113b",
            # exactly as the director did).
            rec = run_case_ours(case, arm, workdir)
            if rec["verdict"] != "HARNESS-ERROR":
                R124.check_case(case, rec, markers)
            recs[arm].append(rec)
            print(f"{arm} {case['id']}: {rec['verdict']}", flush=True)
    rows = []
    for bc, ac in zip(recs["loop113c"], recs["loop113d"]):
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
    ok_before_stay_ok = [r["id"] for r in rows
                         if r["before"] == "OK" and r["after"] == "OK"]
    ok_to_bug = [r["id"] for r in rows
                 if r["before"] == "OK" and r["after"] != "OK"]
    bug_to_ok = [r["id"] for r in rows
                 if r["before"] != "OK" and r["after"] == "OK"]
    still_bug = [r["id"] for r in rows if r["after"] != "OK"]
    all_new_wrong = {r["id"]: r["new_wrong_writes"] for r in rows
                     if r["new_wrong_writes"]}
    # Prefix answers: final reply on an abstain-expected turn that is not
    # an abstain (mechanical: after-verdict BUG with an abstain-miss
    # reason on the final turn).
    prefix_after = [r["id"] for r in rows
                    if r["after"] != "OK" and any(
                        "abstain missed" in x for x in r["after_reasons"])]
    out.update({
        "seconds": round(time.time() - t0, 1), "n": n, "rows": rows,
        "ok_before_stay_ok": ok_before_stay_ok, "ok_to_bug": ok_to_bug,
        "bug_to_ok": bug_to_ok, "still_bug": still_bug,
        "prefix_after": prefix_after, "new_wrong_writes": all_new_wrong,
        "pass": len(prefix_after) == 0 and len(all_new_wrong) == 0
        and len(ok_to_bug) == 0,
    })
    (ART / "fable_bench113d_redteam124_report.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"D1: n={n} ok_stay_ok={len(ok_before_stay_ok)} "
          f"ok_to_bug={ok_to_bug} bug_to_ok={bug_to_ok} "
          f"still_bug={still_bug}")
    print(f"D1: prefix_after={prefix_after} "
          f"new_wrong={all_new_wrong} "
          f"-> {'PASS' if out['pass'] else 'FAIL'} "
          f"({out['seconds']} s)")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0 if out["pass"] else 1


def run_case_ours(case: dict, arm: str, workdir: Path) -> dict:
    """Same shape as R124.run_case but with our daemon factories."""
    rec = {"id": case["id"], "family": case["family"], "arm": "loop113b",
           "turns": [], "verdict": "OK", "reasons": []}
    try:
        daemon = make_daemon(arm, workdir)
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 113d D1 redteam124")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
