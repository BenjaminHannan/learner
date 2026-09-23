#!/usr/bin/env python3
"""Experiment 160 -- G3/C2 session152 re-run through loop160 (Muse).

Same semantics as scripts/fable_session152_run.py (fresh daemon dir per
session, mailbox process_file, mechanical judge), with only the target
swapped to loop160 (scripts/fable_loop160_agent.py:Loop160Daemon +
artifacts/fable-correct160-20260922/loop160-config.json, this experiment).
Never overwrites the 152 artifacts: all outputs go to
artifacts/fable-correct160-20260922/. Every reply is diffed against the
sealed T-T run (artifacts/fable-session152-20260922/turns152-T-T-*.json,
read-only): exactly ONE predicted move (S3-teachers-correction turn 6
"no wait, it's denver" UNHELPFUL->OK, +1 write, reply
"Saved: Rao's city is denver."), 0 new WRONG, 0 new writes otherwise.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix160_session152.py
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

import fable_loop160_agent as L160  # noqa: E402 (this experiment)
import fable_session152_run as S152  # noqa: E402 (runner/judge, read-only)
import fable_session152_sessions as SESS  # noqa: E402 (sessions, read-only)

ROOT = SCRIPTS.parent
ART160 = ROOT / "artifacts" / "fable-correct160-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"

# Sealed prediction: the only turn that may differ from the T-T run.
PREDICTED_MOVES = {("S3-teachers-correction", 6): {
    "verdict": "OK", "fact_writes": 1,
    "reply": "Saved: Rao's city is denver.\n"}}


def main() -> int:
    t0 = time.time()
    ART160.mkdir(parents=True, exist_ok=True)
    cfg0 = json.loads((ART160 / "loop160-config.json").read_text(
        encoding="utf-8"))
    summary: dict = {}
    diffs: list[dict] = []
    new_wrong = 0
    for s in SESS.SESSIONS:
        root = ART160 / "work-session160" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(cfg0)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L160.Loop160Daemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152.run_session(daemon, root, s)
        for t in turns:
            t.update(S152.judge(t))
        (ART160 / f"turns160-T-160-{s['id']}.json").write_text(
            json.dumps(turns, indent=1, ensure_ascii=False), encoding="utf-8")
        sealed = {t["n"]: t for t in json.loads(
            (ART152 / f"turns152-T-T-{s['id']}.json").read_text(
                encoding="utf-8"))}
        counts: dict = {}
        for t in turns:
            counts[t["verdict"]] = counts.get(t["verdict"], 0) + 1
            if t["verdict"] == "WRONG" and sealed[t["n"]][
                    "verdict"] != "WRONG":
                new_wrong += 1
            b = sealed[t["n"]]
            same = (t["reply"] == b["reply"]
                    and t["fact_writes"] == b["fact_writes"]
                    and t["statuses"] == b["statuses"])
            pred = PREDICTED_MOVES.get((s["id"], t["n"]))
            if pred is not None:
                ok = (t["verdict"] == pred["verdict"]
                      and t["fact_writes"] == pred["fact_writes"]
                      and t["reply"] == pred["reply"])
                diffs.append({"session": s["id"], "n": t["n"],
                              "predicted": True, "as_predicted": ok,
                              "reply": t["reply"],
                              "verdict": t["verdict"],
                              "fact_writes": t["fact_writes"]})
            elif not same:
                diffs.append({"session": s["id"], "n": t["n"],
                              "predicted": False, "as_predicted": False,
                              "reply": t["reply"], "base_reply": b["reply"],
                              "verdict": t["verdict"],
                              "base_verdict": b["verdict"],
                              "fact_writes": t["fact_writes"],
                              "base_writes": b["fact_writes"]})
        summary[s["id"]] = counts
        print(f"T-160 {s['id']}: {counts}", flush=True)
    unpredicted = [d for d in diffs if not d["predicted"]]
    unmet = [d for d in diffs if d["predicted"] and not d["as_predicted"]]
    total = round(time.time() - t0, 1)
    out = {"summary": summary, "seconds": total, "diffs_vs_TT": diffs,
           "unpredicted_diffs": len(unpredicted), "unmet_predictions": len(
               unmet), "new_wrong": new_wrong}
    (ART160 / "run160-session152-summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"unpredicted={len(unpredicted)} unmet={len(unmet)} "
          f"new_wrong={new_wrong} TOTAL {total} s")
    return 0 if (not unpredicted and not unmet and new_wrong == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
