#!/usr/bin/env python3
"""Experiment 151, Q1: paired no-"?" probe (32 pairs + 22 non-questions).

Each pair runs in TWO identical fresh daemon dirs through the mailbox
(teaches first, then the question): once with the no-"?" form, once with
its byte-exact "?" twin. Sealed bar: no-"?" reply EQUALS "?" reply
exactly, 32/32. Each non-question runs in a fresh dir: sealed bar is
0 notebook writes and a marker-carrying clarify (no confident fact).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_qmark151_q1.py --variant 151
  (... --variant qrewrite)
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
MY_ART = ROOT / "artifacts" / "fable-qmark151-20260922"

import fable_qmark151_core as Q151  # noqa: E402 (twin construction)


def dialogue(daemon_cls, cfg: dict, workdir: Path, teaches: list[str],
             question: str) -> dict:
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    daemon = daemon_cls(str(workdir), cfg=dict(copy.deepcopy(cfg)))
    replies: list[str] = []
    events_before_last = 0
    for i, text in enumerate(list(teaches) + [question]):
        if i == len(teaches):
            events_before_last = len(daemon.loop.nb.events)
        fname = f"t{i:02d}.txt"
        (workdir / "inbox" / fname).write_text(str(text) + "\n",
                                              encoding="utf-8")
        daemon.process_file(workdir / "inbox" / fname)
        replies.append((workdir / "outbox" / fname).read_text(
            encoding="utf-8").strip())
    try:
        stage = str(getattr(daemon.loop.ears, "last_stage", ""))
    except Exception:  # noqa: BLE001
        stage = ""
    return {"replies": replies, "reply": replies[-1], "stage": stage,
            "events": len(daemon.loop.nb.events),
            "writes": len(daemon.loop.nb.events) - events_before_last}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 151 Q1 paired probe")
    ap.add_argument("--variant", default="151", choices=["151", "qrewrite"])
    args = ap.parse_args(argv)

    import fable_loop151_agent as M151  # noqa: E402 (this exp)
    if args.variant == "151":
        daemon_cls, cfg = M151.Loop151Daemon, M151.DEFAULT_CONFIG151
    else:
        daemon_cls, cfg = M151.Qmark151Daemon, M151.QMARK151_CONFIG
    tag = "151" if args.variant == "151" else "qrewrite151"

    suite = json.loads((MY_ART / "fable_qmark151_q1.json").read_text(
        encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = MY_ART / f"scratchq1-{tag}"
    t0 = time.time()
    pair_rows: list[dict] = []
    for case in suite["pairs"]:
        twin = Q151.with_question_mark_151(case["noq"])
        a = dialogue(daemon_cls, cfg, scratch / case["id"] / "noq",
                     case["teaches"], case["noq"])
        b = dialogue(daemon_cls, cfg, scratch / case["id"] / "yesq",
                     case["teaches"], twin)
        ok = a["reply"] == b["reply"]
        pair_rows.append({"id": case["id"], "noq": case["noq"], "twin": twin,
                          "noq_reply": a["reply"], "twin_reply": b["reply"],
                          "noq_stage": a["stage"], "twin_stage": b["stage"],
                          "equal": bool(ok)})
        print(f"{case['id']}: {'EQUAL' if ok else 'DIFF'} "
              f"noq={a['reply'][:70]!r} twin={b['reply'][:70]!r}", flush=True)
    nonq_rows: list[dict] = []
    for case in suite["nonquestions"]:
        rec = dialogue(daemon_cls, cfg, scratch / case["id"],
                       case["teaches"], case["text"])
        writes = rec["writes"]
        low = rec["reply"].lower()
        marked = any(m.lower() in low for m in markers)
        ok = (writes == 0) and marked
        nonq_rows.append({"id": case["id"], "text": case["text"],
                          "reply": rec["reply"], "stage": rec["stage"],
                          "writes": int(writes), "marked": bool(marked),
                          "ok": bool(ok)})
        print(f"{case['id']}: {'OK' if ok else 'FLAG'} writes={writes} "
              f"marked={marked} reply={rec['reply'][:70]!r}", flush=True)
    seconds = round(time.time() - t0, 1)
    n_eq = sum(1 for r in pair_rows if r["equal"])
    n_ok = sum(1 for r in nonq_rows if r["ok"])
    (MY_ART / f"fable_qmark151_q1_{tag}_results.json").write_text(
        json.dumps({"seconds": seconds, "variant": tag,
                    "pairs_equal": f"{n_eq}/{len(pair_rows)}",
                    "nonq_ok": f"{n_ok}/{len(nonq_rows)}",
                    "pairs": pair_rows, "nonquestions": nonq_rows},
                   indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"done: pairs {n_eq}/{len(pair_rows)} equal, "
          f"nonquestions {n_ok}/{len(nonq_rows)} ok in {seconds} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
