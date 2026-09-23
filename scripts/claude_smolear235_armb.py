#!/usr/bin/env python3
"""Exp 235 arm B -- the 138i rule reader on each statement turn.

Agent: scripts/claude_loop228_agent.py (= 138i + the 228 flake guard, as the
rules require for new runs on a 138i base) with config
artifacts/fable-agent138i-20260922/loop138i-config.json.
Each statement item gets a fresh isolated workdir; context turns (if any)
are sent first; the frames for the item are the taught triples that are
active after the item's turn and were not active before it.
Question families are not run (scored for arm A only).

python claude_smolear235_armb.py --panel P --work DIR --out OUT.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_smolear235_panel as P  # noqa: E402
import fable_loop90_agent as L90  # noqa: E402
import fable_marks123_all as M  # noqa: E402

AGENT = str(SCRIPTS / "claude_loop228_agent.py")
CONFIG = str(SCRIPTS.parent / "artifacts/fable-agent138i-20260922/loop138i-config.json")
QUESTION_FAMILIES = {"questions", "chain_questions"}


def run_items(items, work):
    mod, dcls, _, _ = M.load_agent(AGENT)
    base = M.load_base_cfg(CONFIG)
    out = {}
    for it in items:
        if it["family"] in QUESTION_FAMILIES:
            continue
        root = Path(work) / f"i_{it['id']}"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        d = M.make_daemon(dcls, base, root)
        turns = list(it["context"]) + [it["turn"]]
        before = set()
        reply = ""
        t0 = time.perf_counter()
        for j, t in enumerate(turns):
            if j == len(turns) - 1:
                before = set(L90.notebook_triples(d.loop.nb))
            f = root / "inbox" / f"m{j:02d}.txt"
            f.write_text(t)
            d.process_file(f)
            reply = (root / "outbox" / f"m{j:02d}.txt").read_text().strip()
        after = set(L90.notebook_triples(d.loop.nb))
        new = sorted(after - before)
        out[it["id"]] = dict(triples=[list(x) for x in new], reply=reply,
                             ms=round((time.perf_counter() - t0) * 1000, 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    items = P.load_panel(a.panel)
    res = run_items(items, a.work)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"arm B: {len(res)} statement items run")


if __name__ == "__main__":
    main()
