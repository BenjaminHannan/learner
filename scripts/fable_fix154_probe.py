#!/usr/bin/env python3
"""Experiment 154 -- Y1/Y2 probe through loop154 (or loop150) by mailbox.

Each case in artifacts/fable-yesno154-20260922/cases154.json runs in ONE
FRESH daemon directory: teaches verbatim, then the yes/no question. Judged
per sealed expectations (yes -> "Yes -- ... <want>"; single-no -> "No --
... <want>"; multi -> "I only know that ... <want>", never No; unknown ->
never No; y2 -> any clarify, never a write). Every seed/case reported,
never averaged. Zero writes on every question turn or the mark fails.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix154_probe.py --agent loop154 \\
    --out artifacts/fable-yesno154-20260922/probe154-loop154.json
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

ROOT = SCRIPTS.parent
ART154 = ROOT / "artifacts" / "fable-yesno154-20260922"


def load_agent(agent: str):
    if agent == "loop154":
        import fable_loop154_agent as L
        return L.Loop154Daemon, copy.deepcopy(L.DEFAULT_CONFIG154)
    if agent == "loop150":
        import fable_loop150_agent as L
        return L.Loop150Daemon, copy.deepcopy(L.DEFAULT_CONFIG150)
    raise ValueError(f"unknown --agent {agent!r}")


def taught_facts(daemon) -> int:
    return sum(1 for e in daemon.loop.nb.events if e.get("kind") == "FACT")


def run_case(case: dict, workroot: Path, daemon_cls, cfg: dict) -> dict:
    root = workroot / case["id"]
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    daemon = daemon_cls(str(root), cfg=dict(cfg))
    n = 0
    for t in case.get("teaches", []):
        n += 1
        name = f"t{n:03d}.txt"
        (root / "inbox" / name).write_text(str(t) + "\n", encoding="utf-8")
        daemon.process_file(root / "inbox" / name)
    before = taught_facts(daemon)
    n += 1
    qname = f"t{n:03d}.txt"
    (root / "inbox" / qname).write_text(str(case["question"]) + "\n",
                                        encoding="utf-8")
    daemon.process_file(root / "inbox" / qname)
    reply = (root / "outbox" / qname).read_text(encoding="utf-8").strip()
    writes = taught_facts(daemon) - before
    try:
        stage = str(getattr(daemon.loop.ears, "last_stage", ""))
    except Exception:
        stage = ""
    return {"id": case["id"], "group": case["group"],
            "expect": case["expect"], "question": case["question"],
            "reply": reply, "fact_writes": writes, "ears_stage": stage}


def judge(row: dict, want) -> dict:
    reply, expect = row["reply"], row["expect"]
    low = reply.lower()
    writes = row["fact_writes"]
    if writes != 0:
        return {"verdict": "WRONG", "why": f"question wrote {writes}"}
    if expect == "yes":
        ok = reply.startswith("Yes \u2014") and (want or "") in reply
        return {"verdict": "OK" if ok else "WRONG",
                "why": "yes+want" if ok else f"want Yes+{want!r}: {reply[:90]!r}"}
    if expect == "no-single":
        ok = reply.startswith("No \u2014") and (want or "") in reply
        return {"verdict": "OK" if ok else "WRONG",
                "why": "no+want" if ok else f"want No+{want!r}: {reply[:90]!r}"}
    if expect == "only-know":
        ok = ("only know" in low and not reply.startswith("No \u2014")
              and (want or "") in reply)
        return {"verdict": "OK" if ok else "WRONG",
                "why": ("only-know+want" if ok
                        else f"want only-know+{want!r}, never No: {reply[:90]!r}")}
    if expect == "unknown":
        ok = not reply.startswith("No \u2014")
        return {"verdict": "OK" if ok else "WRONG",
                "why": ("honest non-No" if ok
                        else f"unknown said No: {reply[:90]!r}")}
    if expect == "nowrite":
        return {"verdict": "OK", "why": "clarify, no write"}
    return {"verdict": "HARNESS-ERROR", "why": f"bad expect {expect!r}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 154 yes/no probe")
    ap.add_argument("--agent", default="loop154",
                    choices=("loop154", "loop150"))
    ap.add_argument("--out", default=str(ART154 / "probe154-loop154.json"))
    args = ap.parse_args()
    daemon_cls, cfg = load_agent(args.agent)
    cases = json.loads((ART154 / "cases154.json").read_text(encoding="utf-8"))
    workroot = ART154 / f"scratch-probe-{args.agent}"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    rows = []
    for case in cases:
        row = run_case(case, workroot, daemon_cls, cfg)
        row.update(judge(row, case.get("want")))
        rows.append(row)
        print(f"{row['id']:6s} {row['expect']:9s} -> {row['verdict']:5s} "
              f"w={row['fact_writes']} {row['reply'][:80]!r}", flush=True)
    y1 = [r for r in rows if r["group"] in (
        "yes", "twohop", "single-no", "multi", "unknown")]
    y2 = [r for r in rows if r["group"] == "y2"]
    wrong = [r["id"] for r in y1 if r["verdict"] != "OK"]
    y2bad = [r["id"] for r in y2 if r["verdict"] != "OK"]
    out = {
        "agent": args.agent, "seconds": round(time.time() - t0, 1),
        "y1_n": len(y1), "y1_wrong": wrong,
        "y1_yes": sum(1 for r in y1 if r["expect"] == "yes"),
        "y1_single_no": sum(1 for r in y1 if r["expect"] == "no-single"),
        "y1_multi": sum(1 for r in y1 if r["expect"] == "only-know"),
        "y1_unknown": sum(1 for r in y1 if r["expect"] == "unknown"),
        "y1_twohop": sum(1 for r in y1 if r["group"] == "twohop"),
        "y2_n": len(y2), "y2_bad": y2bad,
        "pass": not wrong and not y2bad,
        "rows": rows,
    }
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(f"Y1 {len(y1)} cases wrong={wrong} | Y2 {len(y2)} bad={y2bad} | "
          f"{out['seconds']} s -> {'PASS' if out['pass'] else 'FAIL'}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
