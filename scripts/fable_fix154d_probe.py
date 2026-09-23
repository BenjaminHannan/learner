#!/usr/bin/env python3
"""Experiment 154d T1 -- sealed 38-turn dialogue through loop154d vs loop138f.

One fresh Loop154dDaemon dir and one fresh Loop138fDaemon dir run the
sealed dialogue (artifacts/fable-yesno154d-20260922/cases154d.json) in
lockstep through the mailbox (process_file per turn, idle_seconds passed
explicitly). Judged per sealed expectations:

  teach        -> 154d reply byte-identical to the 138f reply
  yes          -> reply EXACTLY the sealed "Yes, ..." string, 0 writes
  no-single    -> reply EXACTLY the sealed "No, ..." string, 0 writes
  only-know    -> reply EXACTLY the sealed "Not that I know of. ..." string,
                  0 writes (never "No")
  fall-through -> 154d reply byte-identical to the 138f reply, 0 writes

Every group count, every wrong answer and every write is reported; any
deviation fails the mark (rc=1). No existing file is read except the case
file and the two agent modules (read-only imports).

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix154d_probe.py \\
    --out artifacts/fable-yesno154d-20260922/probe154d-loop154d.json
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

import fable_loop138f_agent as L138f  # noqa: E402 (base arm, read-only)
import fable_loop154d_agent as L154d  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-yesno154d-20260922"


def fresh_daemon(daemon_cls, cfg: dict, root: Path):
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return daemon_cls(str(root), cfg=cfg, idle_seconds=5.0)


def facts(daemon) -> int:
    return sum(1 for e in daemon.loop.nb.events if e.get("kind") == "FACT")


def drive(daemon, root: Path, turns: list[str]) -> list[dict]:
    out = []
    for i, text in enumerate(turns, 1):
        name = f"t{i:03d}.txt"
        (root / "inbox" / name).write_text(str(text) + "\n", encoding="utf-8")
        before = facts(daemon)
        daemon.process_file(root / "inbox" / name)
        reply = (root / "outbox" / name).read_text(encoding="utf-8").strip()
        out.append({"n": i, "turn": text, "reply": reply,
                    "fact_writes": facts(daemon) - before})
    return out


def judge(case: dict, got: dict, base: dict) -> dict:
    expect = case.get("expect")
    writes = got["fact_writes"]
    if expect == "teach":
        ok = got["reply"] == base["reply"]
        return {"verdict": "OK" if ok else "WRONG",
                "why": "teach-identical" if ok else
                f"teach reply moved: {got['reply'][:100]!r} vs "
                f"{base['reply'][:100]!r}"}
    if writes != 0:
        return {"verdict": "WRONG-WRITE",
                "why": f"question turn wrote {writes} fact(s)"}
    if expect in ("yes", "no-single", "only-know"):
        want = case.get("want", "")
        ok = got["reply"] == want
        if expect == "only-know" and got["reply"].startswith("No,"):
            return {"verdict": "WRONG", "why": "multi relation said No"}
        return {"verdict": "OK" if ok else "WRONG",
                "why": f"{expect}+want" if ok else
                f"want {want!r}, got {got['reply'][:120]!r}"}
    if expect == "fall-through":
        ok = got["reply"] == base["reply"]
        return {"verdict": "OK" if ok else "WRONG",
                "why": "fall-identical" if ok else
                f"fall-through moved: {got['reply'][:100]!r} vs "
                f"{base['reply'][:100]!r}"}
    return {"verdict": "WRONG", "why": f"unknown expect {expect!r}"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 154d T1 probe")
    ap.add_argument("--cases", default=str(ART / "cases154d.json"))
    ap.add_argument("--out", default=str(ART / "probe154d-loop154d.json"))
    ap.add_argument("--workroot", default=None)
    args = ap.parse_args(argv)

    spec = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    cases = spec["cases"]
    workroot = Path(args.workroot) if args.workroot else Path(args.out).parent
    t0 = time.time()
    cfg154d = copy.deepcopy(L154d.DEFAULT_CONFIG154D)
    cfg154d["sleep_threshold"] = 100000
    cfg138f = copy.deepcopy(L138f.DEFAULT_CONFIG138F)
    cfg138f["sleep_threshold"] = 100000
    d154d = fresh_daemon(L154d.Loop154dDaemon, cfg154d,
                         workroot / "work-probe154d")
    d138f = fresh_daemon(L138f.Loop138fDaemon, cfg138f,
                         workroot / "work-probe138f")
    turns = [c["turn"] for c in cases]
    got = drive(d154d, workroot / "work-probe154d", turns)
    base = drive(d138f, workroot / "work-probe138f", turns)
    rows = []
    for case, g, b in zip(cases, got, base):
        j = judge(case, g, b)
        rows.append({**g, "group": case.get("group"),
                     "expect": case.get("expect"),
                     "fall": case.get("fall", ""),
                     "want": case.get("want", ""),
                     "base_reply": b["reply"], **j})
    from collections import Counter
    counter = dict(Counter(r["verdict"] for r in rows))
    groups = {}
    for r in rows:
        groups.setdefault(r["group"], []).append(r["verdict"])
    summary = {"id": spec.get("id"), "n": len(rows), "counter": counter,
               "groups": {k: {"n": len(v), "ok": sum(1 for x in v
                                                     if x == "OK")}
                          for k, v in groups.items()},
               "wrong_answers": [r["n"] for r in rows
                                 if r["verdict"] == "WRONG"],
               "writes": [r["n"] for r in rows if r["fact_writes"]],
               "seconds": round(time.time() - t0, 1)}
    Path(args.out).write_text(json.dumps({"summary": summary, "rows": rows},
                                         indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(f"T1: n={summary['n']} {counter} groups={summary['groups']} "
          f"in {summary['seconds']}s -> {args.out}", flush=True)
    for r in rows:
        if r["verdict"] != "OK":
            print(f"  FAIL n={r['n']} {r['turn']!r}: {r['why']}", flush=True)
    rc = 0 if (counter.get("OK", 0) == len(rows)) else 1
    print(f"T1 rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
