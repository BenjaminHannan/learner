#!/usr/bin/env python3
"""Exp 129a marks P2/P3/P4 -- loop102 red-team98 + L1-L6 + innocent re-run
on loop129a (F3 identity check vs the reported loop117 outcomes).

Same sealed suites + judges as scripts/fable_loop117_marks.py (R98 judge,
RC.CASES, sealed run-2 verdicts, loop96 L-runners, sealed 30 innocents);
only the agent under test is loop129a (factories from
scripts/fable_fix129_common.py; kill9 reboot script is the 129a agent).

  P2  64 sealed redteam98 cases; bar: 0 OK->BUG and 0 still-BUG vs sealed
      run-2 (loop117's outcome), every change listed.
  P3  L1-L6 via the loop96 runners with the 129a agent swapped in (runtime
      attribute patch only); bar: all 7 pass (loop117's outcome).
  P4  30 sealed innocent sentences; bar: pass with 0 false refusals.

Writes under artifacts/fable-fix129-20260922/ (never elsewhere).
Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop129a_marks.py --mark all
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix129_common as C129  # noqa: E402 (this experiment)
import fable_loop129a_agent as L129a  # noqa: E402 (this experiment)
import fable_loop96_agent as L96  # noqa: E402 (before-arm refs, read-only)
import fable_redteam98_cases as RC  # noqa: E402 (sealed, read-only)
import fable_redteam98_runner as R98  # noqa: E402 (judge, read-only)

ROOT = SCRIPTS.parent
ART = C129.ART129
ART98 = ROOT / "artifacts" / "fable-redteam98-20260921"
ART102 = ROOT / "artifacts" / "fable-loop102-20260921"


def run_p2(out: Path) -> dict:
    t0 = time.time()
    workroot = out / "p2-129a-tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    sealed = json.loads((ART98 / "fable_redteam98_results.json").read_text(
        encoding="utf-8"))
    base_verdict = {c["id"]: (c.get("verdict"),
                              c.get("observed_final", "")[:160])
                    for c in sealed["cases"]}
    rows = []
    for case in RC.CASES:
        res = C129.run_case(case, workroot, C129.new_daemon129a,
                            C129.SCRIPT129A)
        verdict = R98.judge(case, res)
        final = next(
            (e["reply"] for e in reversed(res["log"])
             if e["file"] not in ("RESTART", "TEAR-TAIL", "KILL9-SUMMARY")),
            "")[:160]
        b_verdict, b_final = base_verdict[case["id"]]
        rows.append({"id": case["id"], "group": case["group"],
                     "sealed_verdict": b_verdict,
                     "loop129a_verdict": verdict["verdict"],
                     "reason": verdict.get("reason", "")[:200],
                     "reply_changed": (final != b_final),
                     "loop129a_final": final})
        print(f"P2-129a {case['id']}: sealed={b_verdict} "
              f"129a={verdict['verdict']}", flush=True)
    ok_to_bug = [r["id"] for r in rows
                 if r["sealed_verdict"] == "OK"
                 and r["loop129a_verdict"] == "BUG"]
    bug_to_ok = [r["id"] for r in rows
                 if r["sealed_verdict"] == "BUG"
                 and r["loop129a_verdict"] == "OK"]
    still_bug = [r["id"] for r in rows
                 if r["loop129a_verdict"] == "BUG"]
    reply_changed_ok = [r["id"] for r in rows
                        if r["sealed_verdict"] == "OK"
                        and r["loop129a_verdict"] == "OK"
                        and r["reply_changed"]]
    rep = {"mark": "P2-129a", "n": len(rows), "ok_to_bug": ok_to_bug,
           "bug_to_ok": bug_to_ok, "still_bug": still_bug,
           "reply_changed_ok_ok": reply_changed_ok,
           "pass": len(ok_to_bug) == 0 and len(still_bug) == 0,
           "seconds": round(time.time() - t0, 1), "rows": rows}
    (out / "p2-129a-report.json").write_text(json.dumps(rep, indent=1),
                                             encoding="utf-8")
    print(f"P2-129a: OK->BUG={ok_to_bug} BUG->OK={bug_to_ok} "
          f"stillBUG={still_bug} okReplyChanged={reply_changed_ok} "
          f"-> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


def run_p3(out: Path, only: str | None = None) -> dict:
    t0 = time.time()
    import fable_loop96_marks as M96  # noqa: E402 (runners reused, read-only)
    p3out = out / "p3-129a"
    p3out.mkdir(parents=True, exist_ok=True)
    # Agent swap by runtime attribute patch only; no file is edited.
    L96.build_agent96 = L129a.build_agent129a
    L96.DEFAULT_CONFIG96 = L129a.DEFAULT_CONFIG129A
    M96.PY96 = list(C129.PY129A)

    def daemon_cfg129a(state_dir: Path) -> dict:
        return C129.cfg129a(state_dir)
    M96.daemon_cfg96 = daemon_cfg129a
    runners = {"l1": M96.run_l1, "l2": M96.run_l2, "l3": M96.run_l3,
               "l4": M96.run_l4, "l5z1": M96.run_l5z1, "l5z2": M96.run_l5z2,
               "l6": M96.run_l6}
    selected = [only] if only else list(runners)
    reps = {}
    ok = True
    for name in selected:
        rep = runners[name](p3out)
        reps[name] = {"pass": bool(rep["pass"]),
                      "seconds": rep.get("seconds")}
        ok = ok and bool(rep["pass"])
    rep = {"mark": "P3-129a", "selected": selected, "pass": bool(ok),
           "seconds": round(time.time() - t0, 1), "marks": reps}
    (out / f"p3-129a-report-{only or 'all'}.json").write_text(
        json.dumps(rep, indent=1), encoding="utf-8")
    print(f"P3-129a({only or 'all'}): -> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


def show_value(nb, value: dict) -> str:
    if "entity" in value:
        return nb.entities.get(value["entity"], f"?{value['entity']}")
    return str(value.get("literal"))


def run_p4(out: Path) -> dict:
    t0 = time.time()
    p4 = json.loads((ART102 / "p4-innocent-30.json").read_text(
        encoding="utf-8"))
    (out / "p4-129a-tmp").mkdir(parents=True, exist_ok=True)
    rows = []
    for item in p4["sentences"]:
        root = Path(tempfile.mkdtemp(prefix="p4_",
                                     dir=str(out / "p4-129a-tmp")))
        (root / "inbox").mkdir(exist_ok=True)
        d = C129.new_daemon129a(root)
        log: list = []
        nb = d.loop.nb
        steps = list(item.get("setup", [])) + [item["text"]]
        for j, text in enumerate(steps):
            if j == len(steps) - 1:
                before_facts = set(nb.facts)
                before_entities = dict(nb.entities)
            p = root / "inbox" / f"s{j:02d}.txt"
            p.write_text(text, encoding="utf-8")
            C129.process_pending(d, root, log)
        exp = item.get("expect", {})
        row = {"id": item["id"], "text": item["text"],
               "replies": [e["reply"].strip()[:160] for e in log]}
        if "stored_value" in exp or "stored_entity_suffix" in exp:
            last = log[-1]
            new_facts = [(fid, nb.facts[fid]["relation"],
                          show_value(nb, nb.facts[fid]["value"]))
                         for fid in set(nb.facts) - before_facts
                         if fid in nb.facts]
            new_entities = [name for eid, name in nb.entities.items()
                            if eid not in before_entities]
            lits = [v for _, _, v in new_facts]
            ents = list(new_entities)
            if "stored_value" in exp:
                row.update({"stored": lits,
                            "pass": exp["stored_value"] in lits})
            else:
                row.update({"stored_entities": ents,
                            "pass": any(exp["stored_entity_suffix"] in e
                                        for e in ents)})
            row["false_refusal"] = (not row["pass"]
                                    and last["fact_writes"] == 0)
        else:
            got = log[-1]["reply"]
            row.update({"pass": exp["ask_contains"] in got,
                        "false_refusal": exp["ask_contains"] not in got})
        rows.append(row)
        print(f"P4-129a {item['id']}: {'PASS' if row['pass'] else 'FAIL'} "
              f":: {item['text'][:70]!r} -> {row['replies'][-1][:90]!r}",
              flush=True)
    refusals = [r["id"] for r in rows if r.get("false_refusal")]
    bad = [r["id"] for r in rows if not r["pass"]]
    rep = {"mark": "P4-129a", "n": len(rows), "false_refusals": refusals,
           "nonpass": bad,
           "pass": len(refusals) <= 2 and len(bad) == 0,
           "seconds": round(time.time() - t0, 1), "rows": rows}
    (out / "p4-129a-report.json").write_text(json.dumps(rep, indent=1),
                                             encoding="utf-8")
    print(f"P4-129a: false_refusals={refusals} nonpass={bad} "
          f"-> {'PASS' if rep['pass'] else 'FAIL'}")
    return rep


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 129a marks")
    parser.add_argument("--mark", choices=("p2", "p3", "l1", "l2",
                                           "l3", "l4", "l5z1", "l5z2",
                                           "l6", "p4", "all"),
                        required=True)
    parser.add_argument("--out", default=str(ART))
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "p4-129a-tmp").mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    oks = []
    if args.mark in ("p2", "all"):
        oks.append(bool(run_p2(out)["pass"]))
    if args.mark == "p3":
        oks.append(bool(run_p3(out)["pass"]))
    elif args.mark in ("l1", "l2", "l3", "l4", "l5z1", "l5z2", "l6"):
        oks.append(bool(run_p3(out, args.mark)["pass"]))
    if args.mark == "all":
        for name in ("l1", "l2", "l3", "l4", "l5z1", "l5z2", "l6"):
            oks.append(bool(run_p3(out, name)["pass"]))
    if args.mark in ("p4", "all"):
        oks.append(bool(run_p4(out)["pass"]))
    print(f"MARKS129A {'PASS' if all(oks) else 'FAIL'} "
          f"({round(time.time() - t0, 1)} s)")
    return 0 if all(oks) else 1


if __name__ == "__main__":
    sys.exit(main())
