#!/usr/bin/env python3
"""Exp 245 runner: one fresh work dir per item, both arms interleaved.

Each item (a JSON line with "id", "setup", "question") is run on base228
(scripts/claude_loop228_agent.py) and on 245 (scripts/claude_loop245_agent.py),
item by item, arms alternating, so the per-question timing is measured in
the same session. Output: one JSON line per item per arm with setup replies,
stored triples after setup and after the question, the reply, and the
question's wall time in ms.

Usage:
  python -B scripts/claude_run245.py --cases FILE --work DIR --out OUT.jsonl
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_marks123_all as M  # noqa: E402 (read-only harness helpers)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import claude_loop228_agent as A228  # noqa: E402 (base arm)
import claude_loop245_agent as A245  # noqa: E402 (fix arm)

CFGS = {"base228": "artifacts/claude-determinism228-20260922/loop228-config.json",
        "fix245": "artifacts/claude-myrel245-20260922/loop245-config.json"}
ARMS = {"base228": A228.Loop228Daemon, "fix245": A245.Loop245Daemon}


def _triples(d):
    return sorted([list(t) for t in L90.notebook_triples(d.loop.nb)])


def _turn(d, root: Path, j: int, text: str) -> tuple[str, float]:
    f = root / "inbox" / f"m{j:02d}.txt"
    f.write_text(text)
    t0 = time.perf_counter()
    d.process_file(f)
    ms = (time.perf_counter() - t0) * 1000.0
    return (root / "outbox" / f"m{j:02d}.txt").read_text().strip(), ms


def run_item(arm: str, item: dict, work: Path, cfgs) -> dict:
    base_cfg = cfgs[arm]
    root = work / arm / item["id"]
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    d = M.make_daemon(ARMS[arm], base_cfg, root)
    setup_replies = []
    for j, t in enumerate(item["setup"]):
        rep, _ = _turn(d, root, j, t)
        setup_replies.append(rep)
    after_setup = _triples(d)
    reply, ms = _turn(d, root, len(item["setup"]), item["question"])
    return {"id": item["id"], "arm": arm, "setup_replies": setup_replies,
            "stored_after_setup": after_setup, "reply": reply,
            "stored_after_question": _triples(d), "q_ms": round(ms, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--arms", default="base228,fix245")
    args = ap.parse_args(argv)
    cfgs = {arm: M.load_base_cfg(path) for arm, path in CFGS.items()}
    items = [json.loads(x) for x in Path(args.cases).read_text().splitlines()
             if x.strip()]
    arms = args.arms.split(",")
    work = Path(args.work)
    with open(args.out, "w", encoding="utf-8") as out:
        for k, item in enumerate(items):
            order = arms if k % 2 == 0 else list(reversed(arms))
            for arm in order:
                row = run_item(arm, item, work, cfgs)
                out.write(json.dumps(row) + "\n")
                out.flush()
    print(f"wrote {args.out}: {len(items)} items x {len(arms)} arms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
