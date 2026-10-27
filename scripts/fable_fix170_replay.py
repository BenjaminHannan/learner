#!/usr/bin/env python3
"""Exp 170 replay driver: one arm, one case file, record replies + state.

Usage (one process per arm; never import both agents in one process):
  python -B scripts/fable_fix170_replay.py --agent loop138d|loop170 \\
      --cases <cases.json> --src <notebook-src-dir|empty> --work <workdir> --out <out.json>

Cases file: {"turns": [...], "seed": N}. Records per-turn replies plus final
notebook digest (canonical facts sha256, event count, events tail sha).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def canonical_facts(loop) -> str:
    facts = loop.nb.facts
    items = []
    for fid in sorted(facts.keys()):
        f = facts[fid]
        items.append([fid, f.get("subject"), f.get("relation"),
                      json.dumps(f.get("value"), sort_keys=True),
                      f.get("source"), f.get("n"),
                      f.get("supersedes"), bool(loop.nb.active(fid))])
    return json.dumps(items, sort_keys=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 170 one-arm replay")
    ap.add_argument("--agent", required=True, choices=["loop138d", "loop170"])
    ap.add_argument("--cases", required=True)
    ap.add_argument("--src", required=True,
                    help="'empty' for a fresh notebook, else a dir to copy")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sleep-threshold", type=int, default=100000)
    args = ap.parse_args(argv)

    if args.agent == "loop138d":
        import fable_loop138d_agent as M
        build, key = M.build_agent138d, "DEFAULT_CONFIG138D"
    else:
        import fable_loop170_agent as M
        build, key = M.build_agent170, "DEFAULT_CONFIG170"

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    turns = cases["turns"]
    work = Path(args.work)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    if args.src == "empty":
        src = work / "fresh"
        src.mkdir(parents=True)
    else:
        src = work / "nbcopy"
        shutil.copytree(args.src, src)
    cfg = copy.deepcopy(getattr(M, key))
    cfg["state_dir"] = str(src)
    cfg["sleep_threshold"] = args.sleep_threshold
    t0 = time.time()
    loop = build(cfg)
    boot_s = round(time.time() - t0, 1)
    replies = []
    ms = []
    for tx in turns:
        u0 = time.process_time()
        said = loop.turn(tx)
        ms.append(round((time.process_time() - u0) * 1000.0, 2))
        replies.append(" ".join(said) if said else "(nothing to say)")
    facts_sha = hashlib.sha256(
        canonical_facts(loop).encode("utf-8")).hexdigest()
    try:
        nev = len(loop.nb.events)
    except Exception:
        nev = -1
    out = {"agent": args.agent, "seed": cases.get("seed"),
           "n_turns": len(turns), "boot_s": boot_s,
           "seconds": round(time.time() - t0, 1),
           "replies": replies, "ask_ms": ms,
           "facts_sha": facts_sha, "n_events": nev}
    Path(args.out).write_text(json.dumps(out), encoding="utf-8")
    print(f"replay {args.agent}: {len(turns)} turns in {out['seconds']}s",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
