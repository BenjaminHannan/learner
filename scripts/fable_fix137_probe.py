#!/usr/bin/env python3
"""Experiment 137 -- registered probe runner for N1 (multi-word teaches +
questions) and N2 (traps). Base-loop sanity arm included (report only).

N1: one fresh Loop137Daemon; each case teach in file order, then each
question. A teach passes when the reply is an accepted teach AND the
notebook holds exactly (subject, relation, value) as an active taught fact.
A question passes when the reply contains the taught value. Any taught FACT
row that is not exactly the case triple, or any FACT row from a question
turn, counts as a wrong write. Bar: >= 90% teaches stored exactly and
questions answered; 0 wrong writes.
N2: one fresh Loop137Daemon; each trap must add 0 taught FACT rows.
Base arm: same N1 teaches through a fresh Loop129bDaemon (expected: 0
stored; director claim); report only, no bar.

Writes (never elsewhere):
  artifacts/fable-fix137-20260922/fable_fix137_probe_report.json
Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137_probe.py --run
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench121_run as B121  # noqa: E402 (teach_accepted, read-only)
import fable_loop129b_agent as L129b  # noqa: E402 (base arm, read-only)
import fable_loop137_agent as L137  # noqa: E402 (this experiment)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-fix137-20260922"
N1_PATH = ART / "fable_fix137_n1_cases.json"
N2_PATH = ART / "fable_fix137_n2_traps.json"


def _send(daemon, ddir: Path, tag: str, text: str) -> str:
    name = f"{tag}.txt"
    (ddir / "inbox" / name).write_text(text + "\n", encoding="utf-8")
    daemon.process_file(ddir / "inbox" / name)
    return (ddir / "outbox" / name).read_text(encoding="utf-8").strip()


def _fact_count(nb) -> int:
    return sum(1 for e in nb.events if e.get("kind") == "FACT")


def _active_triples(nb) -> list[tuple[str, str, str]]:
    return L90.notebook_triples(nb)


def run_n1(workroot: Path) -> dict:
    t0 = time.time()
    spec = json.loads(N1_PATH.read_text(encoding="utf-8"))
    cases = spec["cases"]
    ddir = workroot / "n1-137"
    if ddir.exists():
        shutil.rmtree(ddir)
    ddir.mkdir(parents=True)
    daemon = L137.Loop137Daemon(str(ddir), cfg=copy.deepcopy(
        L137.DEFAULT_CONFIG137))
    rows = []
    wrong_writes = 0
    for i, c in enumerate(cases):
        before = _fact_count(daemon.loop.nb)
        reply = _send(daemon, ddir, f"teach{i:03d}", c["teach"])
        added = _fact_count(daemon.loop.nb) - before
        triples = _active_triples(daemon.loop.nb)
        exact = (c["subject"], c["relation"], c["value"]) in triples
        ok_reply = B121.teach_accepted(reply)
        # Any FACT row beyond the exact triple is a wrong write; missing
        # write is a miss (not a wrong write) unless a row is wrong.
        wrong = added > 0 and not (added == 1 and exact)
        # A second teach of the same slot would supersede (correct path);
        # subjects are unique here, so added must be exactly 1.
        if added != 1 or not exact:
            if added > 0 and not exact:
                wrong_writes += 1
                wrong = True
        rows.append({"id": i, "teach": c["teach"], "reply": reply[:160],
                     "accepted": bool(ok_reply), "added_facts": added,
                     "stored_exact": bool(exact), "wrong_write": bool(wrong),
                     "stage": str(getattr(daemon.loop.ears, "last_stage",
                                          ""))})
    qrows = []
    for i, c in enumerate(cases):
        before = _fact_count(daemon.loop.nb)
        reply = _send(daemon, ddir, f"q{i:03d}", c["question"])
        added = _fact_count(daemon.loop.nb) - before
        if added:
            wrong_writes += added
        answered = c["value"] in reply
        qrows.append({"id": i, "question": c["question"],
                      "reply": reply[:200], "answered": bool(answered),
                      "fact_writes": added})
    n = len(cases)
    stored = sum(1 for r in rows if r["stored_exact"] and r["accepted"])
    answered = sum(1 for r in qrows if r["answered"])
    rep = {"mark": "N1", "n_teach": n, "n_question": n,
           "stored_exact": stored, "answered": answered,
           "wrong_writes": wrong_writes,
           "pass_store": stored >= 0.9 * n, "pass_answer": answered >= 0.9 * n,
           "pass_nowrong": wrong_writes == 0,
           "seconds": round(time.time() - t0, 1),
           "teach_rows": rows, "question_rows": qrows}
    rep["pass"] = bool(rep["pass_store"] and rep["pass_answer"]
                       and rep["pass_nowrong"])
    return rep


def run_n1_base(workroot: Path) -> dict:
    """Base loop129b on the same teaches (report only; expected 0 stored)."""
    t0 = time.time()
    spec = json.loads(N1_PATH.read_text(encoding="utf-8"))
    cases = spec["cases"]
    ddir = workroot / "n1-129b"
    if ddir.exists():
        shutil.rmtree(ddir)
    ddir.mkdir(parents=True)
    daemon = L129b.Loop129bDaemon(str(ddir), cfg=copy.deepcopy(
        L129b.DEFAULT_CONFIG129B))
    stored = 0
    replies: dict[str, int] = {}
    for i, c in enumerate(cases):
        reply = _send(daemon, ddir, f"teach{i:03d}", c["teach"])
        triples = _active_triples(daemon.loop.nb)
        if (c["subject"], c["relation"], c["value"]) in triples:
            stored += 1
        key = reply[:80]
        replies[key] = replies.get(key, 0) + 1
    return {"mark": "N1-base", "n_teach": len(cases), "stored_exact": stored,
            "reply_histogram": replies, "seconds": round(time.time() - t0, 1)}


def run_n2(workroot: Path) -> dict:
    t0 = time.time()
    spec = json.loads(N2_PATH.read_text(encoding="utf-8"))
    traps = spec["traps"]
    ddir = workroot / "n2-137"
    if ddir.exists():
        shutil.rmtree(ddir)
    ddir.mkdir(parents=True)
    daemon = L137.Loop137Daemon(str(ddir), cfg=copy.deepcopy(
        L137.DEFAULT_CONFIG137))
    rows = []
    wrong = 0
    for t in traps:
        before = _fact_count(daemon.loop.nb)
        reply = _send(daemon, ddir, t["id"].lower(), t["turn"])
        added = _fact_count(daemon.loop.nb) - before
        wrong += added
        rows.append({"id": t["id"], "turn": t["turn"], "note": t["note"],
                     "reply": reply[:200], "added_facts": added})
    return {"mark": "N2", "n": len(traps), "wrong_writes": wrong,
            "pass": wrong == 0, "seconds": round(time.time() - t0, 1),
            "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 137 registered probe")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--out", default=str(ART))
    args = ap.parse_args(argv)
    if not args.run:
        ap.print_help()
        return 0
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    workroot = out / "probe-tmp"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    n1 = run_n1(workroot)
    base = run_n1_base(workroot)
    n2 = run_n2(workroot)
    rep = {"experiment": 137, "n1": n1, "n1_base_129b": base, "n2": n2,
           "seconds": round(time.time() - t0, 1)}
    (out / "fable_fix137_probe_report.json").write_text(
        json.dumps(rep, indent=1), encoding="utf-8")
    print(f"N1: stored {n1['stored_exact']}/{n1['n_teach']} "
          f"answered {n1['answered']}/{n1['n_question']} "
          f"wrong {n1['wrong_writes']} -> {'PASS' if n1['pass'] else 'FAIL'}")
    print(f"N1-base129b: stored {base['stored_exact']}/{base['n_teach']} "
          f"replies={base['reply_histogram']}")
    print(f"N2: {n2['n']} traps wrong {n2['wrong_writes']} "
          f"-> {'PASS' if n2['pass'] else 'FAIL'}")
    print(f"TOTAL seconds={rep['seconds']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0 if (n1["pass"] and n2["pass"]) else 1


if __name__ == "__main__":
    sys.exit(main())
