#!/usr/bin/env python3
"""Experiment 149, W2: new whole-word probe (33 dialogues, sealed before run).

Each case runs in a FRESH daemon dir through the mailbox (teaches first,
then the question), judged with the sealed 143 runner's helpers (imported,
read-only) against the sealed expectations in
artifacts/fable-wordmatch149-20260922/fable_wordmatch149_probe.json.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_wordmatch149_probe.py --variant 149
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
MY_ART = ROOT / "artifacts" / "fable-wordmatch149-20260922"

import fable_redteam143_run as R143  # noqa: E402 (sealed helpers, read-only)


def run_case(case: dict, daemon, workdir: Path, markers: list[str]) -> dict:
    rec = {"id": case["id"], "family": case["family"],
           "expected": case["expected"], "verdict": "OK",
           "teach_replies": [], "reply": "", "extracted": "",
           "stage": "", "reasons": []}
    # NOTE: the daemon was constructed before this call and owns workdir
    # (inbox/outbox/done + notebook); only ensure it exists, never wipe it.
    workdir.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(list(case["teaches"]) + [case["question"]]):
        fname = f"t{i:02d}.txt"
        (workdir / "inbox" / fname).write_text(str(text) + "\n",
                                              encoding="utf-8")
        daemon.process_file(workdir / "inbox" / fname)
        reply = (workdir / "outbox" / fname).read_text(
            encoding="utf-8").strip()
        if i < len(case["teaches"]):
            rec["teach_replies"].append(reply)
            if not R143.teach_accepted(reply):
                rec["verdict"] = "HARNESS-ERROR"
                rec["reasons"].append(f"teach {i} rejected: {reply!r}")
                rec["reply"] = reply
                return rec
        else:
            rec["reply"] = reply
            try:
                rec["stage"] = str(
                    getattr(daemon.loop.ears, "last_stage", ""))
            except Exception:  # noqa: BLE001
                rec["stage"] = ""
    reply = rec["reply"]
    low = reply.lower()
    abst = any(m.lower() in low for m in markers)
    exp = case["expected"]
    rec["extracted"] = R143.extract_answer(reply)
    if exp == "abstain":
        if abst:
            rec["verdict"] = "OK"
        else:
            rec["verdict"] = "WRONG-ANSWER"
            rec["reasons"].append(
                f"confident reply where abstain sealed: {reply!r}")
    else:
        if R143.norm(rec["extracted"]) == R143.norm(exp) and R143.norm(exp):
            rec["verdict"] = "OK"
        elif abst:
            rec["verdict"] = "MISSED"
            rec["reasons"].append(
                f"abstained though answer sealed ({exp!r}): {reply!r}")
        else:
            rec["verdict"] = "WRONG-ANSWER"
            rec["reasons"].append(
                f"confident {rec['extracted']!r} != sealed {exp!r}: {reply!r}")
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 149 W2 probe")
    ap.add_argument("--variant", default="149", choices=["149", "qrewrite"])
    args = ap.parse_args(argv)

    import fable_loop149_agent as M149  # noqa: E402 (this exp)
    if args.variant == "149":
        daemon_cls, cfg = M149.Loop149Daemon, M149.DEFAULT_CONFIG149
    else:
        daemon_cls, cfg = M149.Qrewrite149Daemon, M149.QREWRITE149_CONFIG
    tag = "149" if args.variant == "149" else "qrewrite149"

    suite = json.loads((MY_ART / "fable_wordmatch149_probe.json").read_text(
        encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = MY_ART / f"scratchprobe-{tag}"
    t0 = time.time()
    rows: list[dict] = []
    for case in suite["cases"]:
        workdir = scratch / case["id"]
        if workdir.exists():
            shutil.rmtree(workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        daemon = daemon_cls(str(workdir), cfg=dict(copy.deepcopy(cfg)))
        rec = run_case(case, daemon, workdir, markers)
        rows.append(rec)
        print(f"{case['id']} [{case['family']}]: {rec['verdict']} "
              f"stage={rec['stage']} reply={rec['reply'][:90]!r}", flush=True)
    seconds = round(time.time() - t0, 1)
    (MY_ART / f"fable_wordmatch149_probe_{tag}_results.json").write_text(
        json.dumps({"seconds": seconds, "variant": tag, "rows": rows},
                   indent=1, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print(f"done: {Counter(r['verdict'] for r in rows)} in {seconds} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
