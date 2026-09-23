#!/usr/bin/env python3
"""Experiment 233 runner + scorer (dev cases and the blind panel).

For every case (JSONL: id, family, setup[], question, expect, gold, ...)
a FRESH loop223 daemon and a FRESH loop233 daemon (isolated scratch dirs,
never the repo-root notebook/) each receive the setup turns, then the
question. Recorded per agent: question reply, stored triples before and
after the question (question writes), and question-turn wall time.

Scoring (sealed with PASSMARKS.md):
  abstain(r)   : r contains "i don't know" / "i do not know" (casefold).
  clarify(r)   : r is the 148 NEG or TIME clarify text.
  sheet(r)     : r starts with "I cannot:" or "I can:" (capability sheet).
  valued(r)    : not abstain/clarify/sheet and (r matches "'s <rel> is|are
                 <value>" or starts with "Yes," / "No,").
  right        : expect == answer, gold (casefold) in r, not abstain,
                 not clarify.
  wrong value  : valued(r) and (expect != answer or gold not in r).
  honest abst. : abstain(r) and not wrong value.
  q-write      : stored triples after question != before.
  identical    : reply_233 == reply_223 and triples_233 == triples_223.
  case pass    : polite_taught -> right; polite_untaught -> honest abst.;
                 true_negation / negated_statement -> identical;
                 and never a wrong value or q-write (233 side).

Usage:
  python -B scripts/claude_polite233_run.py --cases F.jsonl --work DIR \
      --out OUT.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import fable_marks123_all as M  # noqa: E402 (daemon factory, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples)
import fable_screen148_mixin as S148  # noqa: E402
import fable_loop223_agent as L223  # noqa: E402
import claude_loop233_agent as L233  # noqa: E402

CFG223 = "artifacts/fable-cantdo223-20260922/loop223-config.json"
CFG233 = "artifacts/claude-polite233-20260922/loop233-config.json"

_VAL_RE = re.compile(r"'s .+ (is|are) .+", re.IGNORECASE)


def abstain(r: str) -> bool:
    lo = r.casefold()
    return "i don't know" in lo or "i do not know" in lo


def clarify(r: str) -> bool:
    return r.strip() in (S148.NEG_MSG, S148.TIME_MSG)


def sheet(r: str) -> bool:
    return r.startswith("I cannot:") or r.startswith("I can:")


def valued(r: str) -> bool:
    if abstain(r) or clarify(r) or sheet(r):
        return False
    return bool(_VAL_RE.search(r)) or r.startswith("Yes,") or \
        r.startswith("No,")


def score_one(case: dict, reply: str) -> dict:
    gold = str(case.get("gold") or "").casefold()
    expect = case.get("expect")
    right = (expect == "answer" and bool(gold) and gold in reply.casefold()
             and not abstain(reply) and not clarify(reply))
    wrong = valued(reply) and (expect != "answer" or not gold
                               or gold not in reply.casefold())
    return {"right": right, "wrong": wrong,
            "honest_abstain": abstain(reply) and not wrong}


def run_agent(daemon_cls, cfg: dict, root: Path, case: dict) -> dict:
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    d = M.make_daemon(daemon_cls, cfg, root)
    setup_replies = []
    for j, t in enumerate(case.get("setup") or []):
        f = root / "inbox" / f"s{j:02d}.txt"
        f.write_text(t, encoding="utf-8")
        d.process_file(f)
        setup_replies.append((root / "outbox" / f.name).read_text(
            encoding="utf-8").strip())
    before = [list(x) for x in L90.notebook_triples(d.loop.nb)]
    f = root / "inbox" / "q.txt"
    f.write_text(case["question"], encoding="utf-8")
    t0 = time.perf_counter()
    d.process_file(f)
    dt = (time.perf_counter() - t0) * 1000.0
    reply = (root / "outbox" / "q.txt").read_text(encoding="utf-8").strip()
    after = [list(x) for x in L90.notebook_triples(d.loop.nb)]
    plain = None
    log = getattr(d.loop, "polite233_log", None)
    if log:
        plain = log[-1]["plain"]
    return {"reply": reply, "setup_replies": setup_replies,
            "triples_before": before, "triples_after": after,
            "qwrite": before != after, "ms": dt, "rewrite": plain}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    cfg223 = M.load_base_cfg(CFG223)
    cfg233 = M.load_base_cfg(CFG233)
    cases = [json.loads(x) for x in Path(args.cases).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    work = Path(args.work)
    rows = []
    for i, case in enumerate(cases):
        # alternate order per case so drift does not favour one agent
        order = [("223", L223.Loop223Daemon, cfg223),
                 ("233", L233.Loop233Daemon, cfg233)]
        if i % 2:
            order.reverse()
        res = {}
        for tag, cls, cfg in order:
            res[tag] = run_agent(cls, cfg, work / f"{case['id']}-{tag}", case)
        a, b = res["223"], res["233"]
        s223, s233 = score_one(case, a["reply"]), score_one(case, b["reply"])
        identical = (a["reply"] == b["reply"]
                     and a["triples_after"] == b["triples_after"])
        fam = case["family"]
        if fam == "polite_taught":
            ok = s233["right"]
        elif fam == "polite_untaught":
            ok = s233["honest_abstain"]
        else:
            ok = identical
        ok = ok and not s233["wrong"] and not b["qwrite"]
        row = {"id": case["id"], "family": fam, "question": case["question"],
               "expect": case.get("expect"), "gold": case.get("gold"),
               "reply223": a["reply"], "reply233": b["reply"],
               "rewrite233": b["rewrite"], "score223": s223,
               "score233": s233, "qwrite223": a["qwrite"],
               "qwrite233": b["qwrite"], "identical": identical,
               "ms223": round(a["ms"], 3), "ms233": round(b["ms"], 3),
               "setup_same": a["setup_replies"] == b["setup_replies"],
               "pass": ok}
        rows.append(row)
        print(f"{case['id']} {fam} {'PASS' if ok else 'MISS'} "
              f"{case['question']!r} -> {b['reply']!r} "
              f"[223: {a['reply']!r}] rw={b['rewrite']!r}", flush=True)
    fams = sorted({r["family"] for r in rows})
    summ = {"n": len(rows), "pass": sum(r["pass"] for r in rows),
            "wrong233": sum(r["score233"]["wrong"] for r in rows),
            "wrong223": sum(r["score223"]["wrong"] for r in rows),
            "qwrite233": sum(r["qwrite233"] for r in rows),
            "qwrite223": sum(r["qwrite223"] for r in rows),
            "setup_diff": sum(not r["setup_same"] for r in rows),
            "families": {}}
    for f in fams:
        fr = [r for r in rows if r["family"] == f]
        summ["families"][f] = {
            "n": len(fr), "pass": sum(r["pass"] for r in fr),
            "right223": sum(r["score223"]["right"] for r in fr),
            "right233": sum(r["score233"]["right"] for r in fr),
            "abstain223": sum(r["score223"]["honest_abstain"] for r in fr),
            "abstain233": sum(r["score233"]["honest_abstain"] for r in fr),
            "identical": sum(r["identical"] for r in fr)}
    diffs = [r["ms233"] - r["ms223"] for r in rows]
    summ["latency_ms"] = {
        "mean223": round(statistics.mean(r["ms223"] for r in rows), 3),
        "mean233": round(statistics.mean(r["ms233"] for r in rows), 3),
        "median_diff": round(statistics.median(diffs), 3),
        "mean_diff": round(statistics.mean(diffs), 3)}
    Path(args.out).write_text(json.dumps({"summary": summ, "rows": rows},
                                         indent=1), encoding="utf-8")
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
