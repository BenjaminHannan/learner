#!/usr/bin/env python3
"""Merge 138k K7 driver: per-turn wall latency through daemon.process_file.

Runs every dialog in the given probe files (restart markers honoured,
restarts not timed) <reps> times on fresh work dirs and records the wall
time of each process_file call. One agent per process (run 138j and 138k
in alternating processes); the scorer compares medians.

usage: claude_merge138k_latency.py <agent.py> <config> <workdir> <reps> <out.json> <probe.json>...
"""
from __future__ import annotations

import gc
import json
import shutil
import statistics
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_marks123_all as M  # noqa: E402 (read-only)


def main() -> int:
    agent, config, work, reps, out = sys.argv[1:6]
    probes = sys.argv[6:]
    _, dcls, _, _ = M.load_agent(agent)
    base = M.load_base_cfg(config)
    dialogs = []
    for p in probes:
        dialogs += json.loads(Path(p).read_text(encoding="utf-8"))
    times = []
    for r in range(int(reps)):
        for i, msgs in enumerate(dialogs):
            root = Path(work) / f"r{r}" / f"d{i:02d}"
            shutil.rmtree(root, ignore_errors=True)
            root.mkdir(parents=True)
            d = M.make_daemon(dcls, base, root)
            k = 0
            for t in msgs:
                if t == "__RESTART__":
                    del d
                    gc.collect()
                    d = M.make_daemon(dcls, base, root)
                    continue
                if t == "__TRIPLES__":
                    continue
                f = root / "inbox" / f"m{k:02d}.txt"
                f.write_text(t)
                t0 = time.perf_counter()
                d.process_file(f)
                times.append((time.perf_counter() - t0) * 1000.0)
                k += 1
            del d
            gc.collect()
    rep = {"agent": agent, "n_turns": len(times),
           "median_ms": statistics.median(times),
           "mean_ms": statistics.fmean(times), "times_ms": times}
    Path(out).write_text(json.dumps(rep), encoding="utf-8")
    print(f"{agent}: n={len(times)} median={rep['median_ms']:.2f} ms "
          f"mean={rep['mean_ms']:.2f} ms", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
