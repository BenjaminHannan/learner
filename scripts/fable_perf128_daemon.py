#!/usr/bin/env python3
"""Exp 128 fast daemon CLI (mirrors fable_daemon108_run --loop102 shape)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fable_agent_loop as G
import fable_perf128_index as F128

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 128 fast loop102 daemon")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--sleep-threshold", type=int, default=G.SLEEP_THRESHOLD)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    root = Path(args.dir)
    root.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else None
    daemon = F128.build_fast_daemon108(root, cfg=cfg, idle_seconds=args.idle_seconds,
                                       sleep_threshold=args.sleep_threshold)
    return daemon.run()

if __name__ == "__main__":
    sys.exit(main())
