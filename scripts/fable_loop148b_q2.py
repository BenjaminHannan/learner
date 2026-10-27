#!/usr/bin/env python3
"""Exp 148b Q2 -- 40-question probe rerun: triggers clarify, innocents match.

Mirror of scripts/fable_loop148_q2.py over the 148b arm: each case runs
through a FRESH Loop148bDaemon (134 lineage) and a FRESH Loop134Daemon
(base). Trigger cases PASS when the 148b reply clarifies (sealed abstain
marker) and the base reply was confident; innocent cases PASS when the two
replies are byte-identical. R1 comparison against 148's report happens in
fable_loop148b_verify.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop148b_q2.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop134_agent as L134  # noqa: E402 (base arm, read-only)
import fable_loop148b_agent as L148b  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-screen148b-20260922"
ART148 = ROOT / "artifacts" / "fable-screen148-20260922"

DUP_ACK = "I already have that."


def run_turns(daemon_cls, cfg, workdir: Path, turns: list[str]) -> list[str]:
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    daemon = daemon_cls(str(workdir), cfg=dict(copy.deepcopy(cfg)))
    replies = []
    for i, text in enumerate(turns):
        fname = f"t{i:02d}.txt"
        (workdir / "inbox" / fname).write_text(str(text) + "\n",
                                               encoding="utf-8")
        daemon.process_file(workdir / "inbox" / fname)
        replies.append((workdir / "outbox" / fname).read_text(
            encoding="utf-8").strip())
    return replies


def teaches_ok(replies: list[str]) -> bool:
    return all(r.startswith("Saved:") or r == DUP_ACK for r in replies[:-1])


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    # 148's sealed case file, read-only (sha sealed in 148's PASSMARKS).
    suite = json.loads((ART148 / "fable_screen148_cases.json").read_text(
        encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch-q2"
    t0 = time.time()
    rows = []
    for case in suite["cases"]:
        turns = list(case["teaches"]) + [case["question"]]
        rnew = run_turns(L148b.Loop148bDaemon, L148b.DEFAULT_CONFIG148B,
                         scratch / "a148b" / case["id"], turns)
        r134 = run_turns(L134.Loop134Daemon, L134.DEFAULT_CONFIG134,
                         scratch / "a134" / case["id"], turns)
        oknew, ok134 = teaches_ok(rnew), teaches_ok(r134)
        qnew, q134 = rnew[-1], r134[-1]
        abstnew = any(m.lower() in qnew.lower() for m in markers)
        abst134 = any(m.lower() in q134.lower() for m in markers)
        if case["kind"] == "trigger":
            verdict = ("OK" if (oknew and ok134 and abstnew and not abst134)
                       else "FAIL")
        else:
            verdict = "OK" if (oknew and ok134 and qnew == q134) else "FAIL"
        rows.append({"id": case["id"], "kind": case["kind"],
                     "verdict": verdict, "reply148b": qnew,
                     "reply134": q134, "abst148b": abstnew,
                     "abst134": abst134})
        print(f"{case['id']} [{case['kind']}]: {verdict} "
              f"base={q134[:70]!r} new={qnew[:70]!r}", flush=True)
    seconds = round(time.time() - t0, 1)
    trig = [r for r in rows if r["kind"] == "trigger"]
    inno = [r for r in rows if r["kind"] == "innocent"]
    rep = {"seconds": seconds,
           "trigger_ok": sum(1 for r in trig if r["verdict"] == "OK"),
           "trigger_n": len(trig),
           "innocent_ok": sum(1 for r in inno if r["verdict"] == "OK"),
           "innocent_n": len(inno),
           "rows": rows}
    (ART / "fable_q2_report148b.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Q2: trigger {rep['trigger_ok']}/{rep['trigger_n']}, "
          f"innocent {rep['innocent_ok']}/{rep['innocent_n']} "
          f"in {seconds} s")
    shutil.rmtree(scratch, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
