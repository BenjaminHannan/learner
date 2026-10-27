#!/usr/bin/env python3
"""Experiment 172b -- G2 comparer: marks172b vs frozen marks154c.

Compares per-case verdict+reply on every suite. Predicted moves
(PASSMARKS, written before the run):
  * p2 B1/B2/B3/B6/B7/B8/F2 -> predicted finals (ask-first behaviour);
    these never count as new WRONG unless the agent writes or answers
    something false (prompt turns must write 0 facts; finals must be
    taught-kept values from the sealed log).
  * rt110 F2/F6/D5 -> predicted IDENTICAL (scan false positives:
    forget empties the slot / vanish never processed).
  * marks-bench suite -> verdict/reply moves only on scan-flagged ids
    (trigger_scan172.json, bench edits are copula re-teaches); prompt-form
    teach-reply diffs only on flagged ids.
  * every other suite/case -> byte-identical semantic fields.

Fails (rc=1) on: any unpredicted move, any new WRONG on unflagged cases,
any false write/answer on predicted cases.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

P2_PRED_FINAL = {
    "B1": "Roberto Merhi's country of citizenship's official language is Spanish.",
    "B2": "Roberto Merhi's country of citizenship's official language is Spanish.",
    "B3": "CM Punk's spouse's languages spoken written or signed is English.",
    "B6": "Poland's capital is Warsaw.",
    "B7": "Roberto Merhi's country of citizenship's official language is Spanish.",
    "B8": "Twitter's chief executive officer's country of citizenship is United States of America.",
    "F2": "Roberto Merhi's country of citizenship's official language is Spanish.",
}
P2_PRED = set(P2_PRED_FINAL)
RT110_PRED_IDENT = {"F2", "F6", "D5"}


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 172b G2 compare")
    ap.add_argument("--mine", required=True)
    ap.add_argument("--frozen", required=True)
    ap.add_argument("--scan", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    mine, frozen = Path(args.mine), Path(args.frozen)
    scan = load(Path(args.scan))
    flagged_bench: set[str] = set(scan.get("bench", {}).get("flagged", {}))
    # Marks-bench suite covers fable_edit_200 + s2fresh_4hop file ids.
    out: dict = {"moves": [], "predicted_ok": [], "failures": []}

    def fail(msg: str) -> None:
        out["failures"].append(msg)
        print(f"FAIL: {msg}", flush=True)

    def move(msg: str) -> None:
        out["moves"].append(msg)
        print(f"MOVE: {msg}", flush=True)

    # -- p2 --
    m2 = load(mine / "p2-report.json")
    f2 = load(frozen / "p2-report.json")
    fb = {r["id"]: r for r in f2["rows"]}
    for r in m2["rows"]:
        b = fb[r["id"]]
        same = (r["agent_verdict"] == b["agent_verdict"]
                and r["agent_final"] == b["agent_final"])
        if r["id"] in P2_PRED:
            pred = P2_PRED_FINAL[r["id"]]
            got = (r["agent_final"] or "").strip()
            if got == pred.strip():
                out["predicted_ok"].append(
                    f"p2/{r['id']}: final as predicted")
            else:
                fail(f"p2/{r['id']}: final {got[:100]!r} != "
                     f"predicted {pred[:100]!r}")
            # False-write audit: prompt turns must write 0 facts.
            for e in r.get("log", []):
                if "Do you want me to change it to" in e.get("reply", "") \
                        and int(e.get("fact_writes", 0) or 0) != 0:
                    fail(f"p2/{r['id']}: prompt turn wrote facts")
            if not same:
                move(f"p2/{r['id']}: predicted move "
                     f"(sealed={b['agent_verdict']}/{b['agent_final'][:60]!r} "
                     f"-> {r['agent_verdict']}/{got[:60]!r})")
        elif not same:
            fail(f"p2/{r['id']}: UNPREDICTED move "
                 f"({b['agent_verdict']}/{b['agent_final'][:80]!r} -> "
                 f"{r['agent_verdict']}/{r['agent_final'][:80]!r})")
            if r["agent_verdict"] == "BUG" and b["agent_verdict"] != "BUG":
                fail(f"p2/{r['id']}: NEW WRONG")

    # -- rt110 --
    m1 = load(mine / "rt110-report.json")
    f1 = load(frozen / "rt110-report.json")
    fb1 = {r["id"]: r for r in f1["rows"]}
    for r in m1["rows"]:
        b = fb1[r["id"]]
        mreps = [e.get("reply", "") for e in r.get("log", [])]
        breps = [e.get("reply", "") for e in b.get("log", [])]
        same = (r["agent_verdict"] == b["agent_verdict"] and mreps == breps)
        if not same:
            if r["id"] in RT110_PRED_IDENT:
                fail(f"rt110/{r['id']}: predicted IDENTICAL but moved")
            else:
                fail(f"rt110/{r['id']}: UNPREDICTED move")
                if r["agent_verdict"] == "BUG" \
                        and b["agent_verdict"] != "BUG":
                    fail(f"rt110/{r['id']}: NEW WRONG")
        elif r["id"] in RT110_PRED_IDENT:
            out["predicted_ok"].append(f"rt110/{r['id']}: identical")

    # -- marks-bench suite (per-item rows in bench-rows-*.jsonl) --
    bench_map = {"bench-rows-fable_edit_200.jsonl": "edit200",
                 "bench-rows-s2fresh_4hop.jsonl": "old_s2fresh_4hop"}
    for fname, tag in bench_map.items():
        mp, fp = mine / fname, frozen / fname
        if not mp.exists() or not fp.exists():
            fail(f"bench/{fname}: missing rows file")
            continue
        mrows = {json.loads(l)["id"]: json.loads(l)
                 for l in mp.read_text(encoding="utf-8").splitlines()
                 if l.strip()}
        frows = {json.loads(l)["id"]: json.loads(l)
                 for l in fp.read_text(encoding="utf-8").splitlines()
                 if l.strip()}
        for rid, r in mrows.items():
            b = frows.get(rid)
            if b is None:
                fail(f"bench/{tag}/{rid}: missing frozen row")
                continue
            flagged = f"{tag}:{rid}" in flagged_bench
            same_verdict = (r.get("verdict") == b.get("verdict")
                            and r.get("reply", "") == b.get("reply", ""))
            teach_same = (r.get("teach_replies", [])
                          == b.get("teach_replies", []))
            if same_verdict and teach_same:
                continue
            if not teach_same and not flagged:
                fail(f"bench/{tag}/{rid}: UNPREDICTED teach-reply diff")
            if not same_verdict:
                if flagged:
                    move(f"bench/{tag}/{rid}: predicted move "
                         f"({b.get('verdict')} -> {r.get('verdict')})")
                else:
                    fail(f"bench/{tag}/{rid}: UNPREDICTED verdict move "
                         f"({b.get('verdict')} -> {r.get('verdict')})")
                    if r.get("verdict") == "wrong" \
                            and b.get("verdict") != "wrong":
                        fail(f"bench/{tag}/{rid}: NEW WRONG")
            elif not teach_same:
                out["predicted_ok"].append(
                    f"bench/{tag}/{rid}: prompt-form teach replies only")

    # -- bench aggregate tables (info only; per-item verdicts above rule) --
    mb = load(mine / "bench-report.json")
    fbb = load(frozen / "bench-report.json")
    for split in mb.get("splits", {}):
        if mb["splits"][split] != fbb["splits"].get(split):
            move(f"bench/{split}: aggregate table differs (see per-item)")

    # -- identical suites (semantic fields) --
    for rep in ("p4-report.json", "q1-report.json", "q4-report.json",
                "rt81-report.json", "sleep-report.json", "soak-report.json",
                "p3-report.json"):
        mp, fp = mine / rep, frozen / rep
        if not mp.exists() or not fp.exists():
            print(f"SKIP {rep}: missing file", flush=True)
            continue
        m, f = load(mp), load(fp)
        # Drop volatile fields (POST-SEAL EDIT 1, see RESULTS: seconds
        # timings, and the agent filename embedded in the sleep SKIP
        # reason -- both name the agent under test by construction).
        for d in (m, f):
            d.pop("seconds", None)
            if isinstance(d.get("table"), list):
                for cell in d["table"]:
                    cell.pop("seconds", None)
            if isinstance(d.get("marks"), dict):
                for cell in d["marks"].values():
                    if isinstance(cell, dict):
                        cell.pop("seconds", None)
            if isinstance(d.get("reason"), str):
                import re as _re
                d["reason"] = _re.sub(r"fable_loop\w+_agent\.py",
                                      "AGENT", d["reason"])
        if m == f:
            out["predicted_ok"].append(f"{rep}: identical")
        else:
            fail(f"{rep}: UNPREDICTED diff")

    (Path(args.out)).write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"moves={len(out['moves'])} predicted_ok="
          f"{len(out['predicted_ok'])} failures={len(out['failures'])}")
    return 1 if out["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
