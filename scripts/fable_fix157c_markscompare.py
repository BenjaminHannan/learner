#!/usr/bin/env python3
"""Exp 157c G2 comparison: per-case verdicts of marks157c vs sealed marks157b.

Read-only analysis helper (prefix fable_fix157c_). Reads the sealed
loop157b reference (artifacts/fable-filler157b-20260922/marks157b/) and
our registered run (artifacts/fable-title157c-20260922/marks157c/),
both read-only, and writes into our own folder only:
marks157c/g2-compare157c.json (+ marks157c/q4-report.json derived from
collected replies via suite_q4/collect_replies, same as the runner).

Compares, per case: p2/p4/rt110 rows, q1 (f5/m5 + replies), rt81 cases,
p3 sub-marks + per-case verdicts, bench rows jsonl, soak counters, sleep
(verdict only; reason MUST differ by agent filename alone), q4 leaks.
Timing fields are ignored. Any move fails G2 honestly.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "artifacts" / "fable-filler157b-20260922" / "marks157b"
NEW = ROOT / "artifacts" / "fable-title157c-20260922" / "marks157c"
sys.path.insert(0, str(ROOT / "scripts"))


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def rows_by_id(report, rowkey="rows", idkey="id"):
    return {r[idkey]: r for r in report.get(rowkey, [])}


def main():
    out = {"moves": [], "notes": []}
    import fable_marks123_all as m123
    q4 = m123.suite_q4(NEW, m123.collect_replies(NEW))
    (NEW / "q4-report.json").write_text(json.dumps(q4, indent=1),
                                        encoding="utf-8")
    out["notes"].append("q4-report.json generated from collected replies: "
                        "leaks=%s pass=%s" % (q4.get("leaks"), q4.get("pass")))

    def move(s):
        out["moves"].append(s)

    for suite in ("p2", "p4", "rt110"):
        ref = load(REF / f"{suite}-report.json")
        new = load(NEW / f"{suite}-report.json")
        rrows, nrows = rows_by_id(ref), rows_by_id(new)
        if set(rrows) != set(nrows):
            move(f"{suite}: case id sets differ "
                 f"ref={len(rrows)} new={len(nrows)}")
            continue
        for cid, rr in sorted(rrows.items()):
            nr = nrows[cid]
            for k in ("sealed_verdict", "agent_verdict"):
                if rr.get(k) != nr.get(k):
                    move(f"{suite} {cid} {k}: ref={rr.get(k)!r} "
                         f"new={nr.get(k)!r}")
            for k in ("agent_final", "reason", "severity"):
                if rr.get(k) != nr.get(k):
                    move(f"{suite} {cid} {k}: ref={rr.get(k)!r} "
                         f"new={nr.get(k)!r}")
        out["notes"].append(f"{suite}: {len(rrows)} cases compared")

    ref, new = load(REF / "q1-report.json"), load(NEW / "q1-report.json")
    for k in ("f5_ok", "m5_ok", "f5_reply", "m5_reply"):
        if ref.get(k) != new.get(k):
            move(f"q1 {k}: ref={ref.get(k)!r} new={new.get(k)!r}")
    out["notes"].append("q1 compared")

    ref, new = load(REF / "rt81-report.json"), load(NEW / "rt81-report.json")
    rrows, nrows = rows_by_id(ref, "cases"), rows_by_id(new, "cases")
    if set(rrows) != set(nrows):
        move(f"rt81: case id sets differ ref={len(rrows)} new={len(nrows)}")
    else:
        for cid, rr in sorted(rrows.items()):
            nr = nrows[cid]
            for k in ("verdict", "observed", "expected", "severity",
                      "facts_delta"):
                if rr.get(k) != nr.get(k):
                    move(f"rt81 {cid} {k}: ref={rr.get(k)!r} "
                         f"new={nr.get(k)!r}")
    out["notes"].append(f"rt81: {len(rrows)} cases compared")

    ref, new = load(REF / "p3-report.json"), load(NEW / "p3-report.json")
    for k, rv in sorted(ref.get("marks", {}).items()):
        nv = new.get("marks", {}).get(k, {})
        if rv.get("pass") != nv.get("pass"):
            move(f"p3 {k} pass: ref={rv.get('pass')} new={nv.get('pass')}")
    out["notes"].append("p3 sub-mark pass flags compared: "
                        + ",".join(sorted(ref.get("marks", {}))))
    for name in ("l2-report.json", "l5z1-report.json", "l5z2-report.json",
                 "l1-report.json", "l3-report.json", "l4-report.json",
                 "l6-report.json"):
        rp, np = REF / "p3" / name, NEW / "p3" / name
        if not rp.exists() or not np.exists():
            out["notes"].append(f"p3/{name}: missing one side, skipped")
            continue
        rr, nn = load(rp), load(np)

        def verdicts(rep):
            found = {}

            def walk(o, path=""):
                if isinstance(o, dict):
                    if "verdict" in o and ("id" in o or "case" in o):
                        found[str(o.get("id", o.get("case")))] = o["verdict"]
                    for kk, vv in o.items():
                        walk(vv, path + "/" + kk)
                elif isinstance(o, list):
                    for i, vv in enumerate(o):
                        walk(vv, path + f"[{i}]")
            walk(rep)
            return found
        rv, nv = verdicts(rr), verdicts(nn)
        if rv and (set(rv) != set(nv) or
                   any(rv[c] != nv[c] for c in rv)):
            bad = [c for c in rv if c not in nv or rv[c] != nv[c]]
            move(f"p3/{name}: {len(bad)} verdict diffs, e.g. {bad[:5]}")
        else:
            out["notes"].append(f"p3/{name}: "
                                f"{len(rv)} per-case verdicts identical"
                                if rv else f"p3/{name}: no per-case "
                                "verdicts, top-level compare")
        if not rv:
            r2 = dict(rr)
            n2 = dict(nn)
            r2.pop("seconds", None)
            n2.pop("seconds", None)
            if r2 != n2:
                move(f"p3/{name}: top-level (non-timing) fields differ")

    for tag in ("fable_edit_200", "s2fresh_4hop"):
        rlines = (REF / f"bench-rows-{tag}.jsonl").read_text(
            encoding="utf-8").splitlines()
        nlines = (NEW / f"bench-rows-{tag}.jsonl").read_text(
            encoding="utf-8").splitlines()
        if len(rlines) != len(nlines):
            move(f"bench {tag}: row counts ref={len(rlines)} "
                 f"new={len(nlines)}")
            continue
        n = 0
        for rl, nl in zip(rlines, nlines):
            ro, no = json.loads(rl), json.loads(nl)
            if ro != no:
                keys = [k for k in set(ro) | set(no)
                        if ro.get(k) != no.get(k)]
                move(f"bench {tag} item {ro.get('id', n)} keys differ: "
                     f"{keys}")
            n += 1
        out["notes"].append(f"bench {tag}: {n} rows compared")

    ref, new = load(REF / "soak-report.json"), load(NEW / "soak-report.json")
    for k in ("turns", "completed", "kill9s", "lost", "wrong",
              "doubled_replies", "audit_lost_pairs", "audit_dup_pairs",
              "audit_wrong_pairs"):
        if ref.get(k) != new.get(k):
            move(f"soak {k}: ref={ref.get(k)!r} new={new.get(k)!r}")
    out["notes"].append("soak counters compared")

    ref = load(REF / "sleep-report.json")
    new = load(NEW / "sleep-report.json")
    if ref.get("skipped") != new.get("skipped"):
        move("sleep skipped flag differs")
    rn = (new.get("reason", "").replace("fable_loop157c_agent.py", "AGENT")
          .replace("157c", "157"))
    rr = ref.get("reason", "").replace("fable_loop157b_agent.py", "AGENT")
    if rn != rr:
        move(f"sleep reason beyond filename: ref={ref.get('reason')!r} "
             f"new={new.get('reason')!r}")
    else:
        out["notes"].append("sleep SKIP reason differs only by filename")

    ref = load(REF / "q4-report.json")
    if ref.get("leaks") != q4.get("leaks"):
        move(f"q4 leaks: ref={ref.get('leaks')!r} new={q4.get('leaks')!r}")
    else:
        out["notes"].append(f"q4 leaks identical ({len(q4['leaks'])} leaks)")
    if ref.get("pass") != q4.get("pass"):
        move("q4 pass flag differs")

    out["pass"] = not out["moves"]
    (NEW / "g2-compare157c.json").write_text(json.dumps(out, indent=1),
                                             encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
